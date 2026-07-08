"""Phase 3d tests: training-facility validation, staffing billing,
population caps, name generation, season_population idempotency."""

from datetime import date

from django.test import TestCase
from rest_framework.exceptions import ValidationError

from accounts.models import User
from clubs.models import Club, Facility, Season, SportLicense
from clubs.services import (cancel_staffing_contract, create_staffing_contract,
                            in_house_price_lc, register_for_season)
from companies.models import DEFAULT_WAGES_LC
from companies.services import found_company, hire_employees
from economy.models import Transaction
from maminho import limits
from players.models import ManagerProfile, Player, SeasonPopulationLog


def make_club(username, name, balance=500000):
    owner = User.objects.create_user(username, password="x", role=User.Role.CLUB_OWNER)
    return Club.objects.create(owner=owner, name=name, country="HR", city="Zagreb",
                               kc_balance=balance)


def make_company(username, name, company_type, workers=0):
    mgr = User.objects.create_user(username, password="x", role=User.Role.MANAGER)
    ManagerProfile.objects.create(user=mgr, kc_balance=1000000)
    company = found_company(mgr, name, company_type)
    if workers:
        hire_employees(company, mgr, workers)
    return company


class TrainingFacilityValidationTests(TestCase):
    """License purchase + season registration must use TRAINING_FACILITY."""

    def test_registration_uses_training_facility(self):
        club = make_club("o1", "Borci Zagreb")
        club.sport_licenses.create(sport="mma")
        season = Season.objects.create(name="S3 2026", sport="mma", status="upcoming",
                                       start_date=date(2026, 9, 1),
                                       end_date=date(2026, 12, 31))
        # sports_hall is mma's EVENT facility — must NOT satisfy registration
        Facility.objects.create(club=club, facility_type="sports_hall", level=3)
        with self.assertRaises(ValidationError):
            register_for_season(club, season)
        # fight_gym is the TRAINING facility — must satisfy it
        Facility.objects.create(club=club, facility_type="fight_gym", level=1)
        registration = register_for_season(club, season)
        self.assertEqual(registration.sport, "mma")

    def test_inactive_sport_blocked(self):
        club = make_club("o2", "Plivaci Split")
        Facility.objects.create(club=club, facility_type="swimming_pool", level=1)
        season = Season.objects.create(name="S3 2026", sport="swimming",
                                       status="upcoming",
                                       start_date=date(2026, 9, 1),
                                       end_date=date(2026, 12, 31))
        club.sport_licenses.create(sport="swimming")  # pre-existing license
        with self.assertRaises(ValidationError):
            register_for_season(club, season)

    def test_mappings_complete_and_capacities_zeroed(self):
        from clubs import facility_config
        for sport in SportLicense.Sport.values:
            self.assertIn(sport, SportLicense.TRAINING_FACILITY)
            self.assertIn(sport, SportLicense.EVENT_FACILITY)
        for ftype in ("fight_gym", "gym"):
            for level in range(1, 8):
                self.assertEqual(
                    facility_config.level_config(ftype, level)["capacity"], 0)


class StaffingContractTests(TestCase):
    def setUp(self):
        self.club = make_club("owner", "NK Test", balance=1000000)
        self.facility = Facility.objects.create(
            club=self.club, facility_type="stadium", level=3)

    def test_in_house_billing(self):
        contract = create_staffing_contract(
            self.club, self.facility.id, "cleaning", in_house=True)
        # stadium L3 needs 4 cleaners; 4 * 300 * 5 = 6000 LC
        expected = 4 * DEFAULT_WAGES_LC["cleaner"] * 5
        self.assertEqual(contract.monthly_price_lc, expected)
        self.assertEqual(in_house_price_lc(self.facility, "cleaning"), expected)
        self.club.refresh_from_db()
        self.assertEqual(self.club.kc_balance, 1000000 - expected)  # first month
        txn = Transaction.objects.get(kind="staffing")
        self.assertEqual(txn.amount, expected)
        self.assertIsNone(txn.to_company)  # central bank

    def test_company_contract_assigns_and_bills(self):
        cleaning_co = make_company("cleaner_ceo", "Cistoca d.o.o.", "cleaning", workers=10)
        contract = create_staffing_contract(
            self.club, self.facility.id, "cleaning",
            provider_company=cleaning_co, monthly_price_lc=2500)
        self.assertEqual(contract.assigned_employees.count(), 4)  # stadium L3
        self.assertEqual(cleaning_co.free_employees().count(), 6)
        cleaning_co.refresh_from_db()
        self.assertEqual(cleaning_co.kc_balance, 2500)
        # maintenance must come from a CONSTRUCTION company, not cleaning
        with self.assertRaises(ValidationError):
            create_staffing_contract(self.club, self.facility.id, "maintenance",
                                     provider_company=cleaning_co,
                                     monthly_price_lc=100)
        # monthly cron bills again
        from django.core.management import call_command
        call_command("process_staffing_billing")
        cleaning_co.refresh_from_db()
        self.assertEqual(cleaning_co.kc_balance, 5000)
        # cancel frees the workers
        cancel_staffing_contract(self.club, contract.id)
        self.assertEqual(cleaning_co.free_employees().count(), 10)

    def test_free_price_and_fully_staffed(self):
        construction_co = make_company("builder_ceo", "Beton d.o.o.",
                                       "construction", workers=5)
        create_staffing_contract(self.club, self.facility.id, "maintenance",
                                 provider_company=construction_co,
                                 monthly_price_lc=0)   # free deals allowed
        self.assertFalse(self.facility.is_fully_staffed)  # cleaning missing
        create_staffing_contract(self.club, self.facility.id, "cleaning",
                                 in_house=True)
        self.assertTrue(self.facility.is_fully_staffed)

    def test_insufficient_workers_blocked(self):
        cleaning_co = make_company("small_ceo", "Mala Cistoca", "cleaning", workers=2)
        with self.assertRaises(ValidationError):  # stadium L3 needs 4
            create_staffing_contract(self.club, self.facility.id, "cleaning",
                                     provider_company=cleaning_co,
                                     monthly_price_lc=1000)


class PopulationCapTests(TestCase):
    def test_company_type_cap(self):
        for i in range(limits.MAX_COMPANIES_PER_TYPE):
            make_company(f"ceo{i}", f"Gradnja {i}", "construction")
        mgr = User.objects.create_user("late_ceo", password="x", role=User.Role.MANAGER)
        ManagerProfile.objects.create(user=mgr, kc_balance=1000000)
        with self.assertRaises(ValidationError):
            found_company(mgr, "Prekasno d.o.o.", "construction")

    def test_manager_registration_cap(self):
        from accounts.serializers import RegisterSerializer
        for i in range(limits.MAX_MANAGERS_PER_LEAGUE):
            u = User.objects.create_user(f"m{i}", password="x", role=User.Role.MANAGER)
            ManagerProfile.objects.create(user=u)
        serializer = RegisterSerializer(data={
            "username": "one_too_many", "email": "x@x.hr",
            "password": "password123", "role": "manager"})
        self.assertFalse(serializer.is_valid())

    def test_roster_cap_constant(self):
        self.assertEqual(limits.MAX_ROSTER_PER_CLUB, 35)


class NameGeneratorTests(TestCase):
    def test_generates_weighted_croatian_names(self):
        from players.namegen import generate_name, hr
        self.assertGreaterEqual(len(hr.FIRST_NAMES), 100)
        self.assertGreaterEqual(len(hr.LAST_NAMES), 200)
        firsts = {n for n, _ in hr.FIRST_NAMES}
        lasts = {n for n, _ in hr.LAST_NAMES}
        for _ in range(50):
            name = generate_name("HR")
            first, rest = name.split(" ", 1)
            self.assertIn(first, firsts)
            self.assertIn(rest, lasts)
        # unknown country falls back to default
        self.assertTrue(generate_name("XX"))

    def test_generate_players_sets_nationality(self):
        from django.core.management import call_command
        call_command("generate_players", 5, sport="football")
        self.assertEqual(Player.objects.filter(nationality="HR").count(), 5)


class SeasonPopulationTests(TestCase):
    def test_retirement_youth_topup_and_idempotency(self):
        from django.core.management import call_command
        mgr_user = User.objects.create_user("m_old", password="x", role=User.Role.MANAGER)
        manager = ManagerProfile.objects.create(user=mgr_user)
        club = make_club("own3", "NK Stari")
        veteran = Player(
            name="Stari Majstor", sport="football", age=36, height_cm=185,
            weight_kg=80, country="Croatia", talent_type="normal",
            is_free_agent=False, current_manager=manager, current_club=club,
            **{f: 10 for f in [
                "agility", "strength", "speed", "acceleration", "jump", "stamina",
                "injury_resistance", "flexibility", "aggression", "bravery",
                "composure", "work_rate", "team_spirit", "influence", "finishing",
                "passing", "dribbling", "first_touch", "crossing", "tackling",
                "marking", "positioning", "off_the_ball", "vision"]})
        veteran.save()

        call_command("season_population", period="S9 9999")

        veteran.refresh_from_db()
        self.assertTrue(veteran.is_retired)
        self.assertFalse(veteran.is_free_agent)
        self.assertIsNone(veteran.current_club)
        self.assertIsNone(veteran.current_manager)

        # youth generated for every active sport, ages 16-18
        for sport in SportLicense.ACTIVE_SPORTS:
            youth = Player.objects.filter(sport=sport, age__lte=18, is_free_agent=True)
            self.assertGreaterEqual(youth.count(), limits.YOUTH_INTAKE_MIN)
        # top-up: pool reaches target
        for sport in SportLicense.ACTIVE_SPORTS:
            pool = Player.objects.filter(sport=sport, is_free_agent=True,
                                         is_retired=False).count()
            self.assertGreaterEqual(pool, limits.FREE_AGENT_POOL_TARGET)

        # idempotent: second run changes nothing
        total_before = Player.objects.count()
        call_command("season_population", period="S9 9999")
        self.assertEqual(Player.objects.count(), total_before)
        self.assertEqual(SeasonPopulationLog.objects.count(), 1)

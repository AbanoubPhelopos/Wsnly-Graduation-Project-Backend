from django.test import SimpleTestCase

from src.Core.Application.Admin.Services.RouteAnalyticsService import (
    RouteAnalyticsQueryValidationError,
    RouteAnalyticsService,
)
from src.Presentation.views.orchestrator import (
    RouteOrchestratorView,
    RouteSearchView,
)


class RouteAnalyticsServiceTests(SimpleTestCase):
    def test_parse_query_options_valid_input(self):
        options = RouteAnalyticsService.parse_query_options(
            {
                "metrics": "requests,avg_duration_seconds",
                "group_by": "day,source",
                "sort": "requests",
                "order": "desc",
                "limit": "25",
                "offset": "10",
            }
        )

        self.assertEqual(options["metrics"], ["requests", "avg_duration_seconds"])
        self.assertEqual(options["group_by"], ["day", "source"])
        self.assertEqual(options["sort"], "requests")
        self.assertEqual(options["order"], "desc")
        self.assertEqual(options["limit"], 25)
        self.assertEqual(options["offset"], 10)

    def test_parse_query_options_invalid_values_raise(self):
        with self.assertRaises(RouteAnalyticsQueryValidationError) as context:
            RouteAnalyticsService.parse_query_options(
                {
                    "metrics": "requests,unknown_metric",
                    "group_by": "day,unknown_group",
                    "sort": "non_existing",
                    "order": "invalid",
                    "limit": "1000",
                    "offset": "-1",
                }
            )

        self.assertIn("Unsupported metrics", str(context.exception))
        self.assertIn("Unsupported group_by", str(context.exception))
        self.assertIn(
            "sort must be one of selected group_by or metrics fields",
            str(context.exception),
        )
        self.assertIn("order must be 'asc' or 'desc'", str(context.exception))


class RouteOrchestratorParsingTests(SimpleTestCase):
    def test_parse_filter_enum_to_preference(self):
        parsed = RouteOrchestratorView._parse_filter({"filter": 3})
        self.assertEqual(parsed, "cheapest")

    def test_parse_current_location_query_fallback(self):
        current = RouteOrchestratorView._parse_current_location(
            {},
            {
                "current_latitude": "30.1",
                "current_longitude": "31.2",
            },
        )
        self.assertEqual(current, (30.1, 31.2))


class RouteSearchViewTests(SimpleTestCase):
    def test_validate_destination_coordinates(self):
        self.assertTrue(RouteSearchView._validate_destination_coordinates(30.1, 31.2))
        self.assertFalse(RouteSearchView._validate_destination_coordinates(95.0, 31.2))

    def test_normalize_text(self):
        self.assertEqual(RouteSearchView._normalize_text("  Abbassia  "), "abbassia")

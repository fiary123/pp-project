import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from src.web.app import app


client = TestClient(app)


def test_nutrition_plan_success():
    payload = {
        "species": "cat",
        "age_months": 18,
        "weight_kg": 4.2,
        "neutered": True,
        "activity_level": "medium",
        "goal": "maintain",
        "food_kcal_per_100g": 380,
        "symptoms": ["软便"],
    }
    resp = client.post("/api/nutrition/plan", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert "plan" in body
    assert "explanation_markdown" in body

    plan = body["plan"]
    for key in [
        "daily_kcal",
        "daily_food_g",
        "feedings_per_day",
        "per_meal_g",
        "daily_water_ml",
        "forbidden_foods",
        "transition_7days",
        "risk_alerts",
    ]:
        assert key in plan


def test_nutrition_plan_invalid_weight():
    payload = {
        "species": "dog",
        "age_months": 12,
        "weight_kg": 0,
        "neutered": False,
        "activity_level": "low",
        "goal": "maintain",
        "food_kcal_per_100g": 360,
        "symptoms": [],
    }
    resp = client.post("/api/nutrition/plan", json=payload)
    assert resp.status_code == 422

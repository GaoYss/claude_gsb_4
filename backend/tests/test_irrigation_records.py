"""灌溉用水记录接口测试。"""

from datetime import date


def irrigation_payload(space, source, **overrides):
    payload = {
        "green_space_id": space.id,
        "water_source_id": source.id,
        "irrigation_date": "2026-03-16",
        "method": "sprinkler",
        "water_volume": 12,
        "duration_minutes": 90,
        "covered_area_sqm": 1000,
        "worker_team": "浇水一班",
        "operator": "王海涛",
    }
    payload.update(overrides)
    return payload


def test_create_irrigation_record_generates_daily_code(api, make_space, make_water_source):
    space = make_space()
    source = make_water_source(space=space)
    data = api.data(
        api.post("/api/v1/irrigation-records", irrigation_payload(space, source)), 201
    )
    assert data["record_no"].startswith("IR-")
    assert data["water_volume"] == 12.0
    assert data["method_label"] == "喷灌"
    assert data["green_space"]["id"] == space.id
    assert data["water_source"]["id"] == source.id


def test_duration_only_is_allowed(api, make_space, make_water_source):
    space = make_space()
    source = make_water_source(space=space)
    data = api.data(
        api.post(
            "/api/v1/irrigation-records",
            irrigation_payload(space, source, water_volume=None),
        ),
        201,
    )
    assert data["water_volume"] is None
    assert data["duration_minutes"] == 90


def test_volume_and_duration_cannot_both_be_empty(api, make_space, make_water_source):
    space = make_space()
    source = make_water_source(space=space)
    response = api.post(
        "/api/v1/irrigation-records",
        irrigation_payload(space, source, water_volume=None, duration_minutes=None),
    )
    assert response.status_code == 422
    assert "至少填写一项" in response.get_json()["data"]["water_volume"]


def test_covered_area_cannot_exceed_green_space_area(api, make_space, make_water_source):
    space = make_space(area_sqm=500)
    source = make_water_source(space=space)
    response = api.post(
        "/api/v1/irrigation-records",
        irrigation_payload(space, source, covered_area_sqm=800),
    )
    assert response.status_code == 422
    assert "覆盖面积" in response.get_json()["data"]["covered_area_sqm"]


def test_water_source_must_exist(api, make_space):
    space = make_space()
    response = api.post(
        "/api/v1/irrigation-records",
        irrigation_payload(space, type("S", (), {"id": 9999})),
    )
    assert response.status_code == 422
    assert "water_source_id" in response.get_json()["data"]


def test_linked_record_must_belong_to_same_space(api, make_space, make_water_source, make_record):
    record = make_record()
    space = make_space(name="无关绿地")
    source = make_water_source(space=space)
    response = api.post(
        "/api/v1/irrigation-records",
        irrigation_payload(space, source, maintenance_record_id=record.id),
    )
    assert response.status_code == 422
    assert "不属于覆盖绿地" in response.get_json()["data"]["maintenance_record_id"]


def test_irrigation_date_cannot_predate_established_date(api, make_space, make_water_source):
    space = make_space(established_date=date(2020, 1, 1))
    source = make_water_source(space=space)
    response = api.post(
        "/api/v1/irrigation-records",
        irrigation_payload(space, source, irrigation_date="2019-01-01"),
    )
    assert response.status_code == 422
    assert "irrigation_date" in response.get_json()["data"]


def test_list_filters_by_district_and_method(api, make_space, make_irrigation):
    space = make_space(district="滨江区")
    make_irrigation(space=space, method="drip")
    make_irrigation(method="hose")

    data = api.data(api.get("/api/v1/irrigation-records", district="滨江区", method="drip"))
    assert data["meta"]["total"] == 1
    assert data["items"][0]["method"] == "drip"


def test_summary_groups_by_district_and_month(api, make_space, make_irrigation):
    space = make_space(district="钱塘区")
    make_irrigation(space=space, irrigation_date=date(2026, 3, 2), water_volume=10)
    make_irrigation(space=space, irrigation_date=date(2026, 3, 20), water_volume=14)
    make_irrigation(space=space, irrigation_date=date(2026, 4, 5), water_volume=8)

    data = api.data(api.get("/api/v1/irrigation-records/summary", district="钱塘区"))
    assert data["total_count"] == 3
    assert data["total_volume"] == 32.0

    rows = {(item["district"], item["month"]): item for item in data["monthly_by_district"]}
    assert rows[("钱塘区", "2026-03")]["total_volume"] == 24.0
    assert rows[("钱塘区", "2026-03")]["count"] == 2
    assert rows[("钱塘区", "2026-04")]["total_volume"] == 8.0


def test_abnormal_high_single_usage_is_flagged(api, make_space, make_irrigation):
    space = make_space(district="临平区")
    make_irrigation(space=space, irrigation_date=date(2026, 5, 2), water_volume=10)
    make_irrigation(space=space, irrigation_date=date(2026, 5, 9), water_volume=12)
    abnormal = make_irrigation(space=space, irrigation_date=date(2026, 5, 16), water_volume=90)

    data = api.data(api.get("/api/v1/irrigation-records/summary", district="临平区"))
    assert data["abnormal_count"] == 1
    bucket = next(
        item for item in data["monthly_by_district"]
        if item["month"] == "2026-05" and item["district"] == "临平区"
    )
    assert bucket["abnormal_count"] == 1
    assert data["abnormal_records"][0]["id"] == abnormal.id
    assert data["abnormal_records"][0]["water_volume"] == 90.0

    listing = api.data(api.get("/api/v1/irrigation-records", district="临平区"))
    flagged = {item["id"]: item["is_abnormal"] for item in listing["items"]}
    assert flagged[abnormal.id] is True

    only_abnormal = api.data(api.get("/api/v1/irrigation-records", abnormal_only="true"))
    assert {item["id"] for item in only_abnormal["items"]} == {abnormal.id}


def test_abnormal_scope_is_district_and_month(api, make_space, make_irrigation):
    """不同行政区或不同月份的高值互不影响异常判定。"""

    space_a = make_space(district="余杭区")
    space_b = make_space(district="富阳区")
    make_irrigation(space=space_a, irrigation_date=date(2026, 6, 3), water_volume=10)
    make_irrigation(space=space_a, irrigation_date=date(2026, 6, 8), water_volume=12)
    big_a = make_irrigation(space=space_a, irrigation_date=date(2026, 6, 15), water_volume=80)
    # 另一行政区同样数值，但因样本独立也构成异常，互不干扰
    make_irrigation(space=space_b, irrigation_date=date(2026, 6, 4), water_volume=11)
    make_irrigation(space=space_b, irrigation_date=date(2026, 6, 9), water_volume=9)
    make_irrigation(space=space_b, irrigation_date=date(2026, 6, 18), water_volume=70)

    data = api.data(api.get("/api/v1/irrigation-records/summary", district="余杭区"))
    assert data["abnormal_count"] == 1
    assert data["abnormal_records"][0]["id"] == big_a.id


def test_small_sample_does_not_trigger_abnormal(api, make_space, make_irrigation):
    space = make_space(district="桐庐县")
    make_irrigation(space=space, irrigation_date=date(2026, 7, 2), water_volume=10)
    make_irrigation(space=space, irrigation_date=date(2026, 7, 9), water_volume=60)

    data = api.data(api.get("/api/v1/irrigation-records/summary", district="桐庐县"))
    assert data["abnormal_count"] == 0


def test_delete_irrigation_record(api, make_irrigation):
    record = make_irrigation()
    api.delete(f"/api/v1/irrigation-records/{record.id}")
    assert api.get(f"/api/v1/irrigation-records/{record.id}").status_code == 404


def test_seeded_data_contains_abnormal_usage(api, seeded):
    data = api.data(api.get("/api/v1/irrigation-records/summary"))
    assert data["total_count"] == seeded["irrigation_record"]
    assert data["total_volume"] > 0
    assert data["abnormal_count"] >= 1
    assert data["abnormal_records"], "演示数据应至少包含一条异常偏高用水"

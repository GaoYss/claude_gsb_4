"""灌溉记录接口测试。"""

from datetime import date


def irrigation_payload(space_id, source_id, **overrides):
    payload = {
        "green_space_id": space_id,
        "water_source_id": source_id,
        "irrigation_date": "2026-08-12",
        "water_amount": 30,
        "team": "浇水一班",
        "operator": "王海涛",
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------- 登记与折算

def test_create_with_amount_is_actual(api, make_space, make_water_source):
    space, source = make_space(), make_water_source()
    data = api.data(api.post("/api/v1/irrigation-records",
                             irrigation_payload(space.id, source.id)), 201)
    assert data["record_no"].startswith("IR-")
    assert data["water_amount"] == 30.0
    assert data["is_estimated"] is False
    assert data["green_space"]["name"] == space.name
    assert data["water_source"]["code"] == source.code


def test_duration_is_estimated_by_flow_rate(api, make_space, make_water_source):
    space = make_space()
    source = make_water_source(flow_rate=20)
    data = api.data(api.post("/api/v1/irrigation-records",
                             irrigation_payload(space.id, source.id,
                                                water_amount=None, duration_hours=3)), 201)
    assert data["water_amount"] == 60.0
    assert data["duration_hours"] == 3.0
    assert data["is_estimated"] is True


def test_amount_and_duration_together_prefers_amount(api, make_space, make_water_source):
    space, source = make_space(), make_water_source(flow_rate=20)
    data = api.data(api.post("/api/v1/irrigation-records",
                             irrigation_payload(space.id, source.id,
                                                water_amount=88, duration_hours=3)), 201)
    assert data["water_amount"] == 88.0
    assert data["is_estimated"] is False


def test_amount_or_duration_is_required(api, make_space, make_water_source):
    space, source = make_space(), make_water_source()
    response = api.post("/api/v1/irrigation-records",
                        irrigation_payload(space.id, source.id, water_amount=None))
    assert response.status_code == 422
    assert "至少填写一项" in response.get_json()["data"]["water_amount"]


def test_duration_without_flow_rate_is_rejected(api, make_space, make_water_source):
    space = make_space()
    source = make_water_source(flow_rate=None)
    response = api.post("/api/v1/irrigation-records",
                        irrigation_payload(space.id, source.id,
                                           water_amount=None, duration_hours=3))
    assert response.status_code == 422
    assert "额定流量" in response.get_json()["data"]["water_amount"]


def test_related_objects_must_exist(api, make_space, make_water_source):
    space, source = make_space(), make_water_source()
    response = api.post("/api/v1/irrigation-records",
                        irrigation_payload(9999, source.id))
    assert response.status_code == 422
    assert "green_space_id" in response.get_json()["data"]
    response = api.post("/api/v1/irrigation-records",
                        irrigation_payload(space.id, 9999))
    assert response.status_code == 422
    assert "water_source_id" in response.get_json()["data"]


def test_date_cannot_precede_established_date(api, make_space, make_water_source):
    space = make_space(established_date=date(2026, 5, 1))
    source = make_water_source()
    response = api.post("/api/v1/irrigation-records",
                        irrigation_payload(space.id, source.id, irrigation_date="2026-04-01"))
    assert response.status_code == 422
    assert "建成日期" in response.get_json()["data"]["irrigation_date"]


# ---------------------------------------------------------------- 更新与重算

def test_update_recomputes_estimation(api, make_space, make_water_source):
    space = make_space()
    source = make_water_source(flow_rate=20)
    created = api.data(api.post("/api/v1/irrigation-records",
                                irrigation_payload(space.id, source.id,
                                                   water_amount=None, duration_hours=3)), 201)
    assert created["water_amount"] == 60.0

    # 只改班组：折算结果保持不变（幂等）
    data = api.data(api.put(f"/api/v1/irrigation-records/{created['id']}",
                            irrigation_payload(space.id, source.id, team="浇水二班",
                                               water_amount=None, duration_hours=3)))
    assert data["team"] == "浇水二班"
    assert data["water_amount"] == 60.0
    assert data["is_estimated"] is True

    # 改时长：按新时长重新折算
    data = api.data(api.put(f"/api/v1/irrigation-records/{created['id']}",
                            irrigation_payload(space.id, source.id,
                                               water_amount=None, duration_hours=5)))
    assert data["water_amount"] == 100.0
    assert data["is_estimated"] is True

    # 改填实际水量：转为实际登记
    data = api.data(api.put(f"/api/v1/irrigation-records/{created['id']}",
                            irrigation_payload(space.id, source.id, water_amount=88,
                                               duration_hours=5)))
    assert data["water_amount"] == 88.0
    assert data["is_estimated"] is False


# ---------------------------------------------------------------- 列表与汇总

def test_list_filters_and_summary(api, make_space, make_water_source, make_irrigation):
    space = make_space()
    source = make_water_source(flow_rate=10)
    make_irrigation(space=space, source=source, water_amount=30)
    make_irrigation(space=space, source=source, water_amount=None, duration_hours=2, team="浇水二班")
    make_irrigation()  # 其他绿地，不计入筛选

    data = api.data(api.get("/api/v1/irrigation-records", green_space_id=space.id))
    assert data["meta"]["total"] == 2
    assert data["summary"]["total_count"] == 2
    assert data["summary"]["total_water_amount"] == 50.0
    assert data["summary"]["estimated_count"] == 1
    assert data["summary"]["estimated_amount"] == 20.0
    assert data["summary"]["total_duration_hours"] == 2.0

    data = api.data(api.get("/api/v1/irrigation-records", estimated="true"))
    assert data["meta"]["total"] == 1
    assert data["items"][0]["is_estimated"] is True

    data = api.data(api.get("/api/v1/irrigation-records", team="浇水二班"))
    assert data["meta"]["total"] == 1


# ---------------------------------------------------------------- 行政区 × 月份汇总

def _make_group_records(make_space, make_water_source, make_irrigation):
    """西湖区 3 条（10/12/100，100 为异常高值）+ 滨江区 1 条（单条不标记）。"""

    source = make_water_source()
    space_a = make_space(district="西湖区")
    space_b = make_space(district="滨江区")
    for amount in (10, 12, 100):
        make_irrigation(space=space_a, source=source, water_amount=amount,
                        irrigation_date=date(2026, 8, 12))
    make_irrigation(space=space_b, source=source, water_amount=500,
                    irrigation_date=date(2026, 8, 13))


def test_monthly_summary_groups_and_flags_anomalies(api, make_space, make_water_source,
                                                    make_irrigation):
    _make_group_records(make_space, make_water_source, make_irrigation)
    data = api.data(api.get("/api/v1/irrigation-records/monthly-summary",
                            month_from="2026-08", month_to="2026-08"))
    assert data["params"]["month_from"] == "2026-08"
    assert data["params"]["anomaly_multiplier"] == 2.0

    groups = {(g["district"], g["month"]): g for g in data["groups"]}
    xh = groups[("西湖区", "2026-08")]
    assert xh["record_count"] == 3
    assert xh["total_water_amount"] == 122.0
    assert xh["anomaly_count"] == 1
    anomaly = xh["anomalies"][0]
    assert anomaly["water_amount"] == 100.0
    assert anomaly["others_avg"] == 11.0
    assert anomaly["ratio"] > 2.0
    assert anomaly["green_space_name"]

    bj = groups[("滨江区", "2026-08")]
    assert bj["record_count"] == 1
    assert bj["anomaly_count"] == 0  # 单条记录的组不标记

    assert data["totals"]["record_count"] == 4
    assert data["totals"]["anomaly_count"] == 1


def test_monthly_summary_splits_estimated_and_filters_district(api, make_space,
                                                               make_water_source, make_irrigation):
    source = make_water_source(flow_rate=10)
    space = make_space(district="西湖区")
    make_irrigation(space=space, source=source, water_amount=30,
                    irrigation_date=date(2026, 8, 12))
    make_irrigation(space=space, source=source, water_amount=None, duration_hours=2,
                    irrigation_date=date(2026, 8, 20))
    make_irrigation(space=make_space(district="滨江区"), source=source, water_amount=40,
                    irrigation_date=date(2026, 8, 13))

    data = api.data(api.get("/api/v1/irrigation-records/monthly-summary",
                            district="西湖区", month_from="2026-08", month_to="2026-08"))
    assert len(data["groups"]) == 1
    group = data["groups"][0]
    assert group["district"] == "西湖区"
    assert group["total_water_amount"] == 50.0
    assert group["estimated_amount"] == 20.0
    assert group["actual_amount"] == 30.0
    assert group["total_duration_hours"] == 2.0


def test_monthly_summary_respects_month_range(api, make_space, make_water_source,
                                              make_irrigation):
    source = make_water_source()
    space = make_space()
    make_irrigation(space=space, source=source, irrigation_date=date(2026, 7, 15))
    make_irrigation(space=space, source=source, irrigation_date=date(2026, 8, 15))

    data = api.data(api.get("/api/v1/irrigation-records/monthly-summary",
                            month_from="2026-08", month_to="2026-08"))
    assert [g["month"] for g in data["groups"]] == ["2026-08"]

    data = api.data(api.get("/api/v1/irrigation-records/monthly-summary",
                            month_from="2026-07", month_to="2026-08"))
    assert [g["month"] for g in data["groups"]] == ["2026-07", "2026-08"]


# ---------------------------------------------------------------- 演示数据

def test_seed_data_includes_irrigation(api, seeded):
    assert seeded["water_source"] == 6
    assert seeded["irrigation_record"] > 0

    # 用宽月份区间覆盖全部演示记录（默认窗口为近 6 个月）
    data = api.data(api.get("/api/v1/irrigation-records/monthly-summary",
                            month_from="2020-01", month_to="2099-12"))
    assert data["totals"]["record_count"] == seeded["irrigation_record"]
    assert data["totals"]["anomaly_count"] > 0  # 演示数据注入了明显偏高记录
    districts = {g["district"] for g in data["groups"]}
    assert districts  # 按行政区分组

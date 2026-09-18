"""水源点接口测试。"""


def source_payload(**overrides):
    payload = {
        "name": "运河取水泵站",
        "district": "拱墅区",
        "address": "运河东路 128 号泵房",
        "source_type": "river",
        "intake_method": "pump",
        "meter_no": "SB-GS-002",
        "flow_rate": 40,
        "status": "normal",
    }
    payload.update(overrides)
    return payload


def test_create_water_source_generates_code(api):
    data = api.data(api.post("/api/v1/water-sources", source_payload()), 201)
    assert data["code"].startswith("WS-")
    assert data["source_type_label"] == "河道取水"
    assert data["intake_method_label"] == "泵站提水"
    assert data["status_label"] == "正常使用"
    assert data["flow_rate"] == 40.0


def test_required_fields_and_enums_are_validated(api):
    response = api.post("/api/v1/water-sources",
                        source_payload(name="", district="", source_type="ocean", flow_rate=-1))
    assert response.status_code == 422
    details = response.get_json()["data"]
    assert "name" in details and "district" in details
    assert "source_type" in details and "flow_rate" in details


def test_list_filters_and_summary(api, make_water_source):
    make_water_source(name="市政供水点", district="拱墅区", source_type="municipal")
    make_water_source(name="雨水调蓄池", district="西湖区", source_type="rainwater",
                      intake_method="gravity", status="maintenance")

    data = api.data(api.get("/api/v1/water-sources", source_type="rainwater"))
    assert data["meta"]["total"] == 1
    assert data["items"][0]["name"] == "雨水调蓄池"

    data = api.data(api.get("/api/v1/water-sources", district="拱墅区"))
    assert data["meta"]["total"] == 1
    assert data["summary"]["total"] == 1
    assert data["summary"]["by_status"] == {"normal": 1}

    summary = api.data(api.get("/api/v1/water-sources/summary"))
    assert summary["total"] == 2
    assert summary["by_status"] == {"normal": 1, "maintenance": 1}


def test_options_exclude_disabled(api, make_water_source):
    make_water_source(name="在用供水点")
    make_water_source(name="已停用供水点", status="disabled")
    data = api.data(api.get("/api/v1/water-sources/options"))
    names = [item["name"] for item in data["items"]]
    assert "在用供水点" in names
    assert "已停用供水点" not in names


def test_update_water_source(api, make_water_source):
    source = make_water_source()
    data = api.data(api.put(f"/api/v1/water-sources/{source.id}",
                            source_payload(name="改名泵站", flow_rate=55, status="maintenance")))
    assert data["name"] == "改名泵站"
    assert data["flow_rate"] == 55.0
    assert data["status"] == "maintenance"
    assert data["code"] == source.code  # 编号不可修改


def test_delete_protection_and_force(api, make_irrigation):
    irrigation = make_irrigation()
    source_id = irrigation.water_source_id

    response = api.delete(f"/api/v1/water-sources/{source_id}")
    assert response.status_code == 409
    assert "灌溉记录" in response.get_json()["message"]

    api.data(api.delete(f"/api/v1/water-sources/{source_id}", force="true"))
    # 强制删除后灌溉记录保留，但解除关联
    record = api.data(api.get(f"/api/v1/irrigation-records/{irrigation.id}"))
    assert record["water_source_id"] is None
    assert record["water_source"] is None

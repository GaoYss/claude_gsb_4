"""灌溉水源点接口测试。"""


def source_payload(space=None, **overrides):
    payload = {
        "name": "运河文化公园中河水口",
        "source_type": "river",
        "district": space.district if space else "拱墅区",
        "address": "运河东路 128 号",
        "status": "active",
        "manager": "俞晓慧",
        "contact_phone": "0571-88221009",
        "installed_date": "2016-05-01",
    }
    if space is not None:
        payload["green_space_id"] = space.id
    payload.update(overrides)
    return payload


def test_create_water_source_generates_yearly_code(api, make_space):
    space = make_space()
    data = api.data(api.post("/api/v1/water-sources", source_payload(space)), 201)
    assert data["source_no"].startswith("WS-")
    assert data["source_type_label"] == "河道取水"
    assert data["status_label"] == "在用"
    assert data["green_space"]["id"] == space.id


def test_water_source_can_be_public_without_green_space(api):
    data = api.data(api.post("/api/v1/water-sources", source_payload()), 201)
    assert data["green_space_id"] is None
    assert data["green_space"] is None


def test_water_source_type_and_phone_validated(api):
    response = api.post("/api/v1/water-sources", source_payload(source_type="tap", contact_phone="??"))
    assert response.status_code == 422
    details = response.get_json()["data"]
    assert "source_type" in details and "contact_phone" in details


def test_unknown_green_space_is_rejected(api):
    response = api.post("/api/v1/water-sources", source_payload(green_space_id=9999))
    assert response.status_code == 422
    assert "green_space_id" in response.get_json()["data"]


def test_list_filters_by_district_and_status(api, make_water_source):
    make_water_source(district="拱墅区", status="active")
    make_water_source(district="余杭区", status="standby")

    data = api.data(api.get("/api/v1/water-sources", district="拱墅区"))
    assert data["meta"]["total"] == 1
    assert data["items"][0]["district"] == "拱墅区"
    assert data["summary"]["by_status"]["active"] == 1

    data = api.data(api.get("/api/v1/water-sources", status="standby"))
    assert data["meta"]["total"] == 1


def test_options_exclude_disabled_and_prefetch_same_district(api, make_space, make_water_source):
    space = make_space(district="西湖区")
    active = make_water_source(space=space, status="active", district="西湖区")
    make_water_source(district="西湖区", status="disabled")
    make_water_source(district="滨江区", status="active")

    data = api.data(api.get("/api/v1/water-sources/options", district="西湖区"))
    ids = {item["id"] for item in data["items"]}
    assert active.id in ids
    assert len(ids) == 1


def test_delete_blocked_when_irrigation_records_exist(api, make_irrigation):
    irrigation = make_irrigation()
    source_id = irrigation.water_source_id

    response = api.delete(f"/api/v1/water-sources/{source_id}")
    assert response.status_code == 409
    assert response.get_json()["data"]["irrigation_record"] >= 1


def test_delete_unused_source(api, make_water_source):
    source = make_water_source()
    api.data(api.delete(f"/api/v1/water-sources/{source.id}"))
    assert api.get(f"/api/v1/water-sources/{source.id}").status_code == 404


def test_source_is_detached_when_green_space_force_deleted(api, make_space, make_water_source):
    space = make_space()
    source = make_water_source(space=space)

    api.data(api.delete(f"/api/v1/green-spaces/{space.id}", force="true"))

    detail = api.data(api.get(f"/api/v1/water-sources/{source.id}"))
    assert detail["green_space_id"] is None
    assert detail["green_space"] is None
    assert detail["status"] == "active"

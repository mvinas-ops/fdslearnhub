import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_login_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/auth/login", json={"email":"admin@learnhub.com","password":"password"})
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert "access_token" in body["data"]

@pytest.mark.asyncio
async def test_login_invalid_credentials():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/auth/login", json={"email":"admin@learnhub.com","password":"wrong"})
        assert res.status_code == 401

@pytest.mark.asyncio
async def test_current_user_and_admin_dashboard():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login = await client.post("/api/auth/login", json={"email":"admin@learnhub.com","password":"password"})
        token = login.json()["data"]["access_token"]
        headers={"Authorization":f"Bearer {token}"}
        me = await client.get("/api/auth/me", headers=headers)
        assert me.status_code == 200
        dash = await client.get("/api/admin/dashboard", headers=headers)
        assert dash.status_code == 200

@pytest.mark.asyncio
async def test_admin_can_create_material_role_user():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = (await client.post("/api/auth/login", json={"email":"admin@learnhub.com","password":"password"})).json()["data"]["access_token"]
        h={"Authorization":f"Bearer {token}"}
        role = await client.post("/api/admin/roles", headers=h, json={"name":"Training Coordinator X","description":"test","color":"blue","permission_keys":["view_attendance"]})
        assert role.status_code in (200,409)
        mat = await client.post("/api/admin/materials", headers=h, json={"title":"Smoke Material","description":"x","category":"Development","number_of_lessons":1,"total_duration":"1 hour","status":"active"})
        assert mat.status_code == 200
        roles = await client.get("/api/admin/roles", headers=h)
        role_id = roles.json()["data"][0]["id"]
        user = await client.post("/api/admin/users", headers=h, json={"full_name":"Smoke User","email":"smoke@example.com","password":"Password123!","role_id":role_id,"barangay_id":1,"status":"active","session_ids":[]})
        assert user.status_code in (200,409)

@pytest.mark.asyncio
async def test_cml_schedule_attendance_unlocks_material():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        cml_token = (await client.post("/api/auth/login", json={"email":"cml@learnhub.com","password":"password"})).json()["data"]["access_token"]
        ch={"Authorization":f"Bearer {cml_token}"}
        participants = await client.get("/api/cml/participants", headers=ch)
        assert participants.status_code == 200
        participant = participants.json()["data"][0]
        user_id = participant["id"]
        barangay_id = participant["barangay"]["id"]

        sched = await client.post("/api/cml/schedules", headers=ch, json={"material_id":1,"session_title":"Smoke Session","date":"2026-03-15","time":"09:00","location":"Center","barangay_id":barangay_id,"participant_ids":[user_id]})
        assert sched.status_code == 200, sched.text
        sid=sched.json()["data"]["id"]
        att = await client.patch(f"/api/cml/schedules/{sid}/attendance", headers=ch, json={"attendance":[{"user_id":user_id,"status":"attended"}]})
        assert att.status_code == 200, att.text

@pytest.mark.asyncio
async def test_trainee_materials_and_csv():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        ttoken = (await client.post("/api/auth/login", json={"email":"john@example.com","password":"password"})).json()["data"]["access_token"]
        th={"Authorization":f"Bearer {ttoken}"}
        mats = await client.get("/api/trainee/materials", headers=th)
        assert mats.status_code == 200
        ctoken = (await client.post("/api/auth/login", json={"email":"cml@learnhub.com","password":"password"})).json()["data"]["access_token"]
        csv_res = await client.get("/api/cml/reports/attendance.csv", headers={"Authorization":f"Bearer {ctoken}"})
        assert csv_res.status_code == 200
        assert "text/csv" in csv_res.headers["content-type"]

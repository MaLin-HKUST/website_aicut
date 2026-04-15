from __future__ import annotations

from app import crud


def test_admin_user_list_allows_admin_without_company(api_client, db_session, as_admin):
    company = crud.admin_create_company(db_session, company_name="日标住建")
    crud.admin_create_user(
        db_session,
        company_id=company.id,
        login_account="rbzj",
        password="user-password",
        user_name="日标住建",
        role="user",
        status="active",
    )

    response = api_client.get("/admin/api/users")

    assert response.status_code == 200
    users = response.json()
    assert any(user["login_account"] == "admin" and user["company_id"] is None for user in users)
    assert any(user["login_account"] == "rbzj" and user["company_id"] == company.id for user in users)


def test_admin_bootstrap_list_endpoints_used_by_frontend(api_client, db_session, as_admin):
    company = crud.admin_create_company(db_session, company_name="住建测试")
    library = crud.admin_create_library(
        db_session,
        company_id=company.id,
        library_name="素材库",
        root_path="/data/materials",
        config_path="/data/config.json",
    )
    group = crud.admin_create_tag_group(
        db_session,
        asset_library_id=library.id,
        group_key="scene",
        group_name="场景",
    )
    crud.admin_create_tag(
        db_session,
        asset_library_id=library.id,
        tag_group_id=group.id,
        tag_key="office",
        tag_name="办公室",
        filter_condition='{"path":"scene","eq":"office"}',
    )

    groups_response = api_client.get("/admin/api/tag-groups")
    tags_response = api_client.get("/admin/api/tags")

    assert groups_response.status_code == 200
    assert tags_response.status_code == 200
    assert any(item["group_key"] == "scene" for item in groups_response.json())
    assert any(item["tag_key"] == "office" for item in tags_response.json())

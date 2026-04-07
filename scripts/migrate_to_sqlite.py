#!/usr/bin/env python3
"""
将线上 PostgreSQL 数据迁移到新的 SQLite 数据库（admin_test 结构）
数据来源: db_backup/server_db_data.sql
"""

import sqlite3
import os
import re
from datetime import datetime

# 配置
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'website_aicut.db')
SQL_FILE = os.path.join(os.path.dirname(__file__), '..', 'db_backup', 'server_db_data.sql')


def generate_id():
    """生成8位随机ID"""
    import uuid
    return uuid.uuid4().hex[:8]


def parse_sql_dump(sql_content):
    """解析 PostgreSQL dump 文件，提取 INSERT 数据"""
    data = {
        'companies': [],
        'users': [],
        'sessions': [],
        'user_usage_monthly': []
    }
    
    # 解析 companies
    companies_match = re.search(
        r"INSERT INTO companies \(id, name, created_at\) VALUES\s*\n(.+?);",
        sql_content, re.DOTALL
    )
    if companies_match:
        for line in companies_match.group(1).split('\n'):
            line = line.strip().rstrip(',')
            if line:
                match = re.match(r"\((\d+),\s*'([^']+)',\s*'([^']+)'\)", line)
                if match:
                    data['companies'].append({
                        'id': int(match.group(1)),
                        'name': match.group(2),
                        'created_at': match.group(3)
                    })
    
    # 解析 users
    users_match = re.search(
        r"INSERT INTO users \(id, username, password_hash, role, company_id, created_at\) VALUES\s*\n(.+?);",
        sql_content, re.DOTALL
    )
    if users_match:
        for line in users_match.group(1).split('\n'):
            line = line.strip().rstrip(',')
            if line:
                match = re.match(
                    r"\((\d+),\s*'([^']+)',\s*'([^']+)',\s*'([^']+)',\s*(NULL|\d+),\s*'([^']+)'\)",
                    line
                )
                if match:
                    data['users'].append({
                        'id': int(match.group(1)),
                        'username': match.group(2),
                        'password_hash': match.group(3),
                        'role': match.group(4),
                        'company_id': None if match.group(5) == 'NULL' else int(match.group(5)),
                        'created_at': match.group(6)
                    })
    
    # 解析 sessions
    sessions_match = re.search(
        r"INSERT INTO sessions \(id, token, user_id, created_at\) VALUES\s*\n(.+?);",
        sql_content, re.DOTALL
    )
    if sessions_match:
        for line in sessions_match.group(1).split('\n'):
            line = line.strip().rstrip(',')
            if line:
                match = re.match(r"\((\d+),\s*'([^']+)',\s*(\d+),\s*'([^']+)'\)", line)
                if match:
                    data['sessions'].append({
                        'id': int(match.group(1)),
                        'token': match.group(2),
                        'user_id': int(match.group(3)),
                        'created_at': match.group(4)
                    })
    
    # 解析 user_usage_monthly
    usage_match = re.search(
        r"INSERT INTO user_usage_monthly \(id, user_id, year_month, credits_used, credits_limit, last_updated, created_at\) VALUES\s*\n(.+?);",
        sql_content, re.DOTALL
    )
    if usage_match:
        for line in usage_match.group(1).split('\n'):
            line = line.strip().rstrip(',')
            if line:
                match = re.match(
                    r"\((\d+),\s*(\d+),\s*'([^']+)',\s*(\d+),\s*(NULL|\d+),\s*'([^']+)',\s*'([^']+)'\)",
                    line
                )
                if match:
                    data['user_usage_monthly'].append({
                        'id': int(match.group(1)),
                        'user_id': int(match.group(2)),
                        'year_month': match.group(3),
                        'credits_used': int(match.group(4)),
                        'credits_limit': None if match.group(5) == 'NULL' else int(match.group(5)),
                        'last_updated': match.group(6),
                        'created_at': match.group(7)
                    })
    
    return data


def create_tables(conn):
    """创建 admin_test 的表结构"""
    cursor = conn.cursor()
    
    cursor.executescript('''
        PRAGMA foreign_keys = ON;
        
        CREATE TABLE IF NOT EXISTS company (
            company_id TEXT PRIMARY KEY,
            company_name TEXT NOT NULL,
            monthly_video_quota INTEGER NOT NULL DEFAULT 0,
            monthly_video_remaining INTEGER NOT NULL DEFAULT 0,
            billing_cycle_start_date TEXT NOT NULL,
            tts_enabled INTEGER NOT NULL DEFAULT 0,
            ai_voice_monthly_usage INTEGER NOT NULL DEFAULT 0,
            ai_voice_usage_start_date TEXT,
            asset_library_id TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS user (
            user_id TEXT PRIMARY KEY,
            company_id TEXT NOT NULL,
            login_account TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            user_name TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES company(company_id)
        );
        
        CREATE TABLE IF NOT EXISTS asset_library (
            asset_library_id TEXT PRIMARY KEY,
            company_id TEXT NOT NULL,
            library_name TEXT NOT NULL,
            root_path TEXT NOT NULL,
            config_path TEXT NOT NULL,
            config_version TEXT,
            config_import_status TEXT NOT NULL DEFAULT 'pending',
            config_import_time DATETIME,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES company(company_id)
        );
        
        CREATE TABLE IF NOT EXISTS asset_library_tag_group (
            tag_group_id TEXT PRIMARY KEY,
            asset_library_id TEXT NOT NULL,
            group_key TEXT NOT NULL,
            group_name TEXT NOT NULL,
            group_order INTEGER DEFAULT 0,
            allow_multi_select INTEGER NOT NULL DEFAULT 1,
            allow_select_all INTEGER NOT NULL DEFAULT 1,
            source_type TEXT NOT NULL DEFAULT 'config',
            status TEXT NOT NULL DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (asset_library_id) REFERENCES asset_library(asset_library_id)
        );
        
        CREATE TABLE IF NOT EXISTS asset_library_tag (
            tag_id TEXT PRIMARY KEY,
            asset_library_id TEXT NOT NULL,
            tag_group_id TEXT NOT NULL,
            tag_key TEXT NOT NULL,
            tag_name TEXT NOT NULL,
            filter_condition TEXT NOT NULL,
            filter_path TEXT,
            source_value TEXT,
            tag_order INTEGER DEFAULT 0,
            is_default_selected INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (asset_library_id) REFERENCES asset_library(asset_library_id),
            FOREIGN KEY (tag_group_id) REFERENCES asset_library_tag_group(tag_group_id)
        );
        
        CREATE TABLE IF NOT EXISTS user_custom_tag_group (
            custom_tag_group_id TEXT PRIMARY KEY,
            company_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            asset_library_id TEXT NOT NULL,
            group_name TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES company(company_id),
            FOREIGN KEY (user_id) REFERENCES user(user_id),
            FOREIGN KEY (asset_library_id) REFERENCES asset_library(asset_library_id)
        );
        
        CREATE TABLE IF NOT EXISTS user_custom_tag_group_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            custom_tag_group_id TEXT NOT NULL,
            tag_id TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (custom_tag_group_id) REFERENCES user_custom_tag_group(custom_tag_group_id),
            FOREIGN KEY (tag_id) REFERENCES asset_library_tag(tag_id)
        );
        
        -- 保留现有业务表
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT NOT NULL UNIQUE,
            user_id TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS user_usage_monthly (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            year_month TEXT NOT NULL,
            credits_used INTEGER DEFAULT 0,
            credits_limit INTEGER,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    
    conn.commit()


def migrate_data(conn, data):
    """迁移数据"""
    cursor = conn.cursor()
    
    # 生成 company ID 映射
    company_id_map = {}
    for company in data['companies']:
        new_id = generate_id()
        company_id_map[company['id']] = new_id
        
        cursor.execute('''
            INSERT INTO company (company_id, company_name, monthly_video_quota, 
                monthly_video_remaining, billing_cycle_start_date, status, created_at)
            VALUES (?, ?, 0, 0, date('now'), 'active', ?)
        ''', (new_id, company['name'], company['created_at']))
    
    print(f"✅ 迁移了 {len(data['companies'])} 个企业")
    
    # 生成 user ID 映射
    user_id_map = {}
    for user in data['users']:
        new_id = generate_id()
        user_id_map[user['id']] = new_id
        
        # 获取 company_id（admin 用户可能没有 company）
        company_id = company_id_map.get(user['company_id'], company_id_map.get(1, generate_id()))
        
        cursor.execute('''
            INSERT INTO user (user_id, company_id, login_account, password, user_name, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'active', ?)
        ''', (new_id, company_id, user['username'], user['password_hash'], user['username'], user['created_at']))
    
    print(f"✅ 迁移了 {len(data['users'])} 个用户")
    
    # 迁移 sessions
    for session in data['sessions']:
        # 查找对应的 user_id
        new_user_id = user_id_map.get(session['user_id'])
        if new_user_id:
            cursor.execute('''
                INSERT INTO sessions (token, user_id, created_at)
                VALUES (?, ?, ?)
            ''', (session['token'], new_user_id, session['created_at']))
    
    print(f"✅ 迁移了 {len(data['sessions'])} 个会话")
    
    # 迁移 usage
    for usage in data['user_usage_monthly']:
        new_user_id = user_id_map.get(usage['user_id'])
        if new_user_id:
            cursor.execute('''
                INSERT INTO user_usage_monthly (user_id, year_month, credits_used, credits_limit, last_updated, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (new_user_id, usage['year_month'], usage['credits_used'], 
                  usage['credits_limit'], usage['last_updated'], usage['created_at']))
    
    print(f"✅ 迁移了 {len(data['user_usage_monthly'])} 条用量记录")
    
    conn.commit()


def main():
    print("🚀 开始数据迁移...")
    print(f"📁 数据库路径: {DB_PATH}")
    print(f"📄 SQL 文件: {SQL_FILE}")
    
    # 确保数据目录存在
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # 读取 SQL 文件
    with open(SQL_FILE, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 解析数据
    data = parse_sql_dump(sql_content)
    print(f"\n📊 解析结果:")
    print(f"   - 企业: {len(data['companies'])} 条")
    print(f"   - 用户: {len(data['users'])} 条")
    print(f"   - 会话: {len(data['sessions'])} 条")
    print(f"   - 用量: {len(data['user_usage_monthly'])} 条")
    
    # 连接数据库
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA foreign_keys = ON')
    
    try:
        # 创建表
        create_tables(conn)
        print("\n✅ 表结构创建完成")
        
        # 迁移数据
        migrate_data(conn, data)
        
        print("\n🎉 数据迁移完成!")
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()

const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const { v4: uuidv4 } = require('uuid');
const path = require('path');
const fs = require('fs');

const app = express();

// 中间件
app.use(express.json());
app.use(express.static('static'));

// 数据库实例（导出供测试使用）
let db = null;

// 初始化数据库
function initDB(dbPath = null) {
    return new Promise((resolve, reject) => {
        // 使用环境变量或默认路径
        const databaseUrl = dbPath || process.env.DB_PATH || path.join(__dirname, 'data', 'admin.db');
        
        // 确保目录存在
        const dir = path.dirname(databaseUrl);
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
        
        db = new sqlite3.Database(databaseUrl, (err) => {
            if (err) {
                reject(err);
                return;
            }
            
            db.serialize(() => {
                // Company 表
                db.run(`
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
                    )
                `);

                // User 表
                db.run(`
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
                    )
                `);

                // Asset Library 表
                db.run(`
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
                    )
                `);

                // Tag Group 表
                db.run(`
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
                    )
                `);

                // Tag 表
                db.run(`
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
                    )
                `);

                // Custom Tag Group 表
                db.run(`
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
                    )
                `);

                // Custom Tag Group Item 表
                db.run(`
                    CREATE TABLE IF NOT EXISTS user_custom_tag_group_item (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        custom_tag_group_id TEXT NOT NULL,
                        tag_id TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (custom_tag_group_id) REFERENCES user_custom_tag_group(custom_tag_group_id),
                        FOREIGN KEY (tag_id) REFERENCES asset_library_tag(tag_id)
                    )
                `, (err) => {
                    if (err) reject(err);
                    else resolve();
                });
            });
        });
    });
}

// 辅助函数
function generateId() {
    return uuidv4().slice(0, 8);
}

function now() {
    return new Date().toISOString();
}

// Promise 化的 db 方法
function dbAll(sql, params = []) {
    return new Promise((resolve, reject) => {
        db.all(sql, params, (err, rows) => {
            if (err) reject(err);
            else resolve(rows);
        });
    });
}

function dbGet(sql, params = []) {
    return new Promise((resolve, reject) => {
        db.get(sql, params, (err, row) => {
            if (err) reject(err);
            else resolve(row);
        });
    });
}

function dbRun(sql, params = []) {
    return new Promise((resolve, reject) => {
        db.run(sql, params, function(err) {
            if (err) reject(err);
            else resolve({ lastID: this.lastID, changes: this.changes });
        });
    });
}

// ============ API 路由 ============

// -------- Company API --------
app.get('/api/companies', async (req, res) => {
    try {
        const companies = await dbAll('SELECT * FROM company ORDER BY created_at DESC');
        res.json(companies);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.post('/api/companies', async (req, res) => {
    try {
        const { company_name, monthly_video_quota, monthly_video_remaining, billing_cycle_start_date, tts_enabled, ai_voice_monthly_usage, status } = req.body;
        
        // 检查企业名称是否已存在
        const existing = await dbGet('SELECT * FROM company WHERE company_name = ?', [company_name]);
        if (existing) {
            return res.status(409).json({ error: 'COMPANY_NAME_EXISTS', message: '企业名称已存在' });
        }
        
        const company_id = generateId();
        
        await dbRun(`
            INSERT INTO company (company_id, company_name, monthly_video_quota, monthly_video_remaining, 
                billing_cycle_start_date, tts_enabled, ai_voice_monthly_usage, status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        `, [company_id, company_name, monthly_video_quota, monthly_video_remaining, 
            billing_cycle_start_date, tts_enabled ? 1 : 0, ai_voice_monthly_usage, status, now()]);
        
        // 查询完整数据返回
        const company = await dbGet('SELECT * FROM company WHERE company_id = ?', [company_id]);
        res.json(company);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.get('/api/companies/:id', async (req, res) => {
    try {
        const company = await dbGet('SELECT * FROM company WHERE company_id = ?', [req.params.id]);
        if (!company) return res.status(404).json({ error: 'Company not found' });
        res.json(company);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.put('/api/companies/:id', async (req, res) => {
    try {
        // 如果修改了企业名称，检查是否与其他企业重复
        if (req.body.company_name) {
            const existing = await dbGet(
                'SELECT * FROM company WHERE company_name = ? AND company_id != ?', 
                [req.body.company_name, req.params.id]
            );
            if (existing) {
                return res.status(409).json({ error: 'COMPANY_NAME_EXISTS', message: '企业名称已存在' });
            }
        }
        
        const fields = [];
        const values = [];
        
        for (const [key, value] of Object.entries(req.body)) {
            if (key === 'tts_enabled') {
                fields.push('tts_enabled = ?');
                values.push(value ? 1 : 0);
            } else {
                fields.push(`${key} = ?`);
                values.push(value);
            }
        }
        
        fields.push('updated_at = ?');
        values.push(now());
        values.push(req.params.id);
        
        await dbRun(`UPDATE company SET ${fields.join(', ')} WHERE company_id = ?`, values);
        res.json({ success: true });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.delete('/api/companies/:id', async (req, res) => {
    try {
        await dbRun('DELETE FROM company WHERE company_id = ?', [req.params.id]);
        res.json({ message: 'Deleted' });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// -------- User API --------
app.get('/api/users', async (req, res) => {
    try {
        const users = await dbAll('SELECT * FROM user ORDER BY created_at DESC');
        res.json(users);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.post('/api/users', async (req, res) => {
    try {
        const { company_id, login_account, password, user_name, status } = req.body;
        const user_id = generateId();
        
        await dbRun(`
            INSERT INTO user (user_id, company_id, login_account, password, user_name, status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        `, [user_id, company_id, login_account, password, user_name, status, now()]);
        
        // 查询完整数据返回
        const user = await dbGet('SELECT * FROM user WHERE user_id = ?', [user_id]);
        res.json(user);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.get('/api/users/:id', async (req, res) => {
    try {
        const user = await dbGet('SELECT * FROM user WHERE user_id = ?', [req.params.id]);
        if (!user) return res.status(404).json({ error: 'User not found' });
        res.json(user);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.put('/api/users/:id', async (req, res) => {
    try {
        const fields = [];
        const values = [];
        
        for (const [key, value] of Object.entries(req.body)) {
            fields.push(`${key} = ?`);
            values.push(value);
        }
        
        fields.push('updated_at = ?');
        values.push(now());
        values.push(req.params.id);
        
        await dbRun(`UPDATE user SET ${fields.join(', ')} WHERE user_id = ?`, values);
        res.json({ success: true });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.delete('/api/users/:id', async (req, res) => {
    try {
        await dbRun('DELETE FROM user WHERE user_id = ?', [req.params.id]);
        res.json({ message: 'Deleted' });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// -------- Asset Library API --------
app.get('/api/libraries', async (req, res) => {
    try {
        const libraries = await dbAll('SELECT * FROM asset_library ORDER BY created_at DESC');
        res.json(libraries);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.post('/api/libraries', async (req, res) => {
    try {
        const { company_id, library_name, root_path, config_path, description, status } = req.body;
        const asset_library_id = generateId();
        
        await dbRun(`
            INSERT INTO asset_library (asset_library_id, company_id, library_name, root_path, config_path, 
                description, status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        `, [asset_library_id, company_id, library_name, root_path, config_path, description, status, now()]);
        
        // 查询完整数据返回
        const library = await dbGet('SELECT * FROM asset_library WHERE asset_library_id = ?', [asset_library_id]);
        res.json(library);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.get('/api/libraries/:id', async (req, res) => {
    try {
        const library = await dbGet('SELECT * FROM asset_library WHERE asset_library_id = ?', [req.params.id]);
        if (!library) return res.status(404).json({ error: 'Library not found' });
        res.json(library);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.put('/api/libraries/:id', async (req, res) => {
    try {
        const fields = [];
        const values = [];
        
        for (const [key, value] of Object.entries(req.body)) {
            fields.push(`${key} = ?`);
            values.push(value);
        }
        
        fields.push('updated_at = ?');
        values.push(now());
        values.push(req.params.id);
        
        await dbRun(`UPDATE asset_library SET ${fields.join(', ')} WHERE asset_library_id = ?`, values);
        res.json({ success: true });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.delete('/api/libraries/:id', async (req, res) => {
    try {
        await dbRun('DELETE FROM asset_library WHERE asset_library_id = ?', [req.params.id]);
        res.json({ message: 'Deleted' });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.post('/api/libraries/:id/import', async (req, res) => {
    try {
        await dbRun(`
            UPDATE asset_library 
            SET config_import_status = 'success', config_import_time = ?, config_version = '1.0', updated_at = ?
            WHERE asset_library_id = ?
        `, [now(), now(), req.params.id]);
        
        res.json({ message: 'Config imported successfully' });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// -------- Tag Group API --------
app.get('/api/libraries/:id/tag-groups', async (req, res) => {
    try {
        const groups = await dbAll('SELECT * FROM asset_library_tag_group WHERE asset_library_id = ?', [req.params.id]);
        res.json(groups);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.post('/api/tag-groups', async (req, res) => {
    try {
        const { asset_library_id, group_key, group_name, group_order, allow_multi_select, allow_select_all } = req.body;
        const tag_group_id = generateId();
        
        await dbRun(`
            INSERT INTO asset_library_tag_group (tag_group_id, asset_library_id, group_key, group_name, 
                group_order, allow_multi_select, allow_select_all, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        `, [tag_group_id, asset_library_id, group_key, group_name, group_order || 0, 
            allow_multi_select ? 1 : 0, allow_select_all ? 1 : 0, now()]);
        
        // 查询完整数据返回
        const tagGroup = await dbGet('SELECT * FROM asset_library_tag_group WHERE tag_group_id = ?', [tag_group_id]);
        res.json(tagGroup);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.put('/api/tag-groups/:id', async (req, res) => {
    try {
        const fields = [];
        const values = [];
        
        for (const [key, value] of Object.entries(req.body)) {
            if (key === 'allow_multi_select' || key === 'allow_select_all') {
                fields.push(`${key} = ?`);
                values.push(value ? 1 : 0);
            } else {
                fields.push(`${key} = ?`);
                values.push(value);
            }
        }
        
        fields.push('updated_at = ?');
        values.push(now());
        values.push(req.params.id);
        
        await dbRun(`UPDATE asset_library_tag_group SET ${fields.join(', ')} WHERE tag_group_id = ?`, values);
        res.json({ success: true });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.delete('/api/tag-groups/:id', async (req, res) => {
    try {
        await dbRun('DELETE FROM asset_library_tag_group WHERE tag_group_id = ?', [req.params.id]);
        res.json({ message: 'Deleted' });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// -------- Tag API --------
app.get('/api/tag-groups/:id/tags', async (req, res) => {
    try {
        const tags = await dbAll('SELECT * FROM asset_library_tag WHERE tag_group_id = ?', [req.params.id]);
        res.json(tags);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.get('/api/libraries/:id/tags', async (req, res) => {
    try {
        const tags = await dbAll('SELECT * FROM asset_library_tag WHERE asset_library_id = ?', [req.params.id]);
        res.json(tags);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.post('/api/tags', async (req, res) => {
    try {
        const { asset_library_id, tag_group_id, tag_key, tag_name, filter_condition, filter_path, tag_order, is_default_selected } = req.body;
        const tag_id = generateId();
        
        await dbRun(`
            INSERT INTO asset_library_tag (tag_id, asset_library_id, tag_group_id, tag_key, tag_name, 
                filter_condition, filter_path, tag_order, is_default_selected, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `, [tag_id, asset_library_id, tag_group_id, tag_key, tag_name, filter_condition, 
            filter_path || null, tag_order || 0, is_default_selected ? 1 : 0, now()]);
        
        // 查询完整数据返回
        const tag = await dbGet('SELECT * FROM asset_library_tag WHERE tag_id = ?', [tag_id]);
        res.json(tag);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.put('/api/tags/:id', async (req, res) => {
    try {
        const fields = [];
        const values = [];
        
        for (const [key, value] of Object.entries(req.body)) {
            if (key === 'is_default_selected') {
                fields.push(`${key} = ?`);
                values.push(value ? 1 : 0);
            } else {
                fields.push(`${key} = ?`);
                values.push(value);
            }
        }
        
        fields.push('updated_at = ?');
        values.push(now());
        values.push(req.params.id);
        
        await dbRun(`UPDATE asset_library_tag SET ${fields.join(', ')} WHERE tag_id = ?`, values);
        res.json({ success: true });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.delete('/api/tags/:id', async (req, res) => {
    try {
        await dbRun('DELETE FROM asset_library_tag WHERE tag_id = ?', [req.params.id]);
        res.json({ message: 'Deleted' });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// -------- Custom Tag Group API --------
app.get('/api/custom-groups', async (req, res) => {
    try {
        const groups = await dbAll('SELECT * FROM user_custom_tag_group ORDER BY created_at DESC');
        res.json(groups);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.get('/api/users/:id/custom-groups', async (req, res) => {
    try {
        const groups = await dbAll('SELECT * FROM user_custom_tag_group WHERE user_id = ?', [req.params.id]);
        res.json(groups);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.post('/api/custom-groups', async (req, res) => {
    try {
        const { company_id, user_id, asset_library_id, group_name, description, tag_ids } = req.body;
        const custom_tag_group_id = generateId();
        
        await dbRun(`
            INSERT INTO user_custom_tag_group (custom_tag_group_id, company_id, user_id, asset_library_id, 
                group_name, description, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        `, [custom_tag_group_id, company_id, user_id, asset_library_id, group_name, description, now()]);
        
        // 插入标签关联
        for (const tag_id of tag_ids || []) {
            await dbRun('INSERT INTO user_custom_tag_group_item (custom_tag_group_id, tag_id) VALUES (?, ?)', 
                [custom_tag_group_id, tag_id]);
        }
        
        // 查询完整数据返回
        const customGroup = await dbGet('SELECT * FROM user_custom_tag_group WHERE custom_tag_group_id = ?', [custom_tag_group_id]);
        res.json(customGroup);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.get('/api/custom-groups/:id', async (req, res) => {
    try {
        const group = await dbGet('SELECT * FROM user_custom_tag_group WHERE custom_tag_group_id = ?', [req.params.id]);
        if (!group) return res.status(404).json({ error: 'Custom group not found' });
        
        const items = await dbAll('SELECT tag_id FROM user_custom_tag_group_item WHERE custom_tag_group_id = ?', [req.params.id]);
        res.json({ group, tag_ids: items.map(i => i.tag_id) });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.put('/api/custom-groups/:id', async (req, res) => {
    try {
        const { group_name, description, tag_ids, status } = req.body;
        
        await dbRun(`
            UPDATE user_custom_tag_group 
            SET group_name = ?, description = ?, status = ?, updated_at = ?
            WHERE custom_tag_group_id = ?
        `, [group_name, description, status, now(), req.params.id]);
        
        // 更新标签关联
        if (tag_ids !== undefined) {
            await dbRun('DELETE FROM user_custom_tag_group_item WHERE custom_tag_group_id = ?', [req.params.id]);
            for (const tag_id of tag_ids) {
                await dbRun('INSERT INTO user_custom_tag_group_item (custom_tag_group_id, tag_id) VALUES (?, ?)', 
                    [req.params.id, tag_id]);
            }
        }
        
        res.json({ success: true });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.delete('/api/custom-groups/:id', async (req, res) => {
    try {
        await dbRun('DELETE FROM user_custom_tag_group_item WHERE custom_tag_group_id = ?', [req.params.id]);
        await dbRun('DELETE FROM user_custom_tag_group WHERE custom_tag_group_id = ?', [req.params.id]);
        res.json({ message: 'Deleted' });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// 导出供测试使用
module.exports = { app, initDB, dbAll, dbGet, dbRun };

const { app, initDB } = require('./app');

const PORT = process.env.PORT || 8001;

// 启动服务器
async function start() {
    await initDB();
    console.log('✅ Database initialized');
    
    app.listen(PORT, () => {
        console.log('');
        console.log('🚀 Admin Service 已启动');
        console.log('');
        console.log(`   📍 访问地址: http://localhost:${PORT}`);
        console.log('');
        console.log('   功能模块:');
        console.log('   • 企业管理');
        console.log('   • 用户管理');
        console.log('   • 素材库管理');
        console.log('   • 标签组/标签管理');
        console.log('   • 用户自定义标签组');
        console.log('');
    });
}

start().catch(console.error);

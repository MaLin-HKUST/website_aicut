# 05. Worker 侧重建步骤

本文回答什么问题：

- Worker 侧应该怎么从当前混乱状态回归正确部署方式
- Worker Gateway 和 Smart Cut Worker 如何各归其位
- Worker 与 A 机器、TOS 应如何重新接通

## 1. Worker 侧目标

Worker 侧最终只承载：

- Worker Gateway
- Smart Cut Worker
- 运行算法所需的执行环境

Worker 侧不承载：

- 网站前端
- admin
- SQLite
- 调度中心 PostgreSQL
- 网站业务 API

## 2. 第一步：明确 Worker 侧输入输出协议

Worker 应从 A 机器接收的不是本地文件路径，而是：

- 调度数据库中的任务信息
- TOS 上的输入对象 key

Worker 应输出：

- 执行状态
- TOS 上的中间产物和最终产物 key

## 3. 第二步：重建 Worker Gateway

Gateway 应承担：

- 注册
- 心跳
- 领取任务
- 从 TOS 拉输入
- 调 Smart Cut Worker
- 把结果上传回 TOS
- 更新 A 机器调度库中的状态

Gateway 不应承担：

- 网站接口
- 调度算法本身
- 算法内容生成

## 4. 第三步：重建 Smart Cut Worker

Smart Cut Worker 应承担：

- 读取输入
- 跑算法
- 输出结果

不应承担：

- TOS 编排
- 调度状态写回
- 设备心跳

## 5. 第四步：接回 A 机器调度中心

Worker 侧重建后，应验证：

- Gateway 能连到 A 机器调度 PostgreSQL
- Gateway 能正确读取 assigned 任务
- Gateway 能回写设备与任务状态

## 6. 第五步：接回 TOS

应验证：

- 输入可从 TOS 获取
- 中间产物可上传 TOS
- 最终产物可上传 TOS
- A 机器网站能通过任务状态看到这些产物引用

## 7. 第六步：为未来多 Worker 做准备

本轮虽可先只用一个 Worker，但设计必须允许：

- 多个 Gateway 同时存在
- 多个执行节点并行处理
- A 机器继续只做中心侧

## 对 Agent 的直接指令

- 不要把 Worker 侧部署设计成“临时放在 A 机器上”。
- 如果你的 Worker 方案仍依赖 A 机器本地目录做跨机器数据交换，说明它还没有回到正确方向。

# Test部署、迭代与发布修复回流

## 正常需求提测门禁

完成全部开发任务和MR合并后，先创建或复用正式【测试】任务，但保持需求=`开发完成`。随后：

1. 从源【交付】正式关系解析唯一非关闭迭代；不得用聊天文本、标题相似或默认迭代代替。无迭代时返回`/skill YunxiaoPM`和`创建迭代`口令。
2. 触发或验证一条覆盖全部适用仓库合并结果的test部署，跟踪到明确成功终态。
3. 证明部署版本包含本需求所有合并Commit/MR；只收到流水线提交成功、运行中、未知或环境不符均阻塞。
4. 在【测试】描述中幂等写入并回读：

```html
<!-- ONEOS_TEST_DEPLOYMENT_EVIDENCE_START -->
<pre>{"schemaVersion":"oneos.test-deployment/v1","projectId":"...","iterationId":"...","iterationName":"...","requirementId":"REQ-1","testTaskId":"TEST-1","executionId":"EXEC-1","environment":"test","status":"success","deployedVersion":"commit-or-artifact","includedChanges":["MR-or-commit"],"evidenceUrl":"...","completedAt":"ISO-8601","idempotencyKey":"test-deploy-..."}</pre>
<!-- ONEOS_TEST_DEPLOYMENT_EVIDENCE_END -->
```

只有该区块与正式项目、迭代、需求、测试任务一致并回读成功，才允许需求`开发完成→待测试`。向YunxiaoQA交接时必须携带迭代ID、执行ID、部署版本和证据URL。

## 发布/验收失败开发回流

```text
/skill yunxiao-development-delivery
处理发布回流：发版任务=TASK-900
```

1. 精确读取发版任务的生产事件或产品验收不通过证据、回滚状态、受影响需求和迭代。
2. 只接受YunxiaoQA已建立且带同一回流批次ID的Bug；若没有正式Bug，零代码写入并交回`接收发布回流`。
3. 冻结当前开发可处理Bug集合，按现有批量修复规则修改、验证并按仓库+分支统一提交；保留逐Bug代码归属。
4. 所有分组合并后只执行一次test部署，证明部署版本覆盖全部回流修复。
5. 将每个成功包含的Bug改为`已修复`，保持验证者不变；不关闭Bug、不写复测通过。
6. 输出：

```text
/skill YunxiaoQA
验证发布回流：发版任务=TASK-900；缺陷=BUG-1,BUG-2；回归证据清单=<JSON文件>
```

开发侧不得直接调用`重新发布`，不得把原生产回滚成功当成修复成功，也不得修改需求、交付或产品验收状态。

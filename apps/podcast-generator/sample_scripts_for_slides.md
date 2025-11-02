---
presentation_title: AgentFlow Lunch & Learn
output_dir: output/slides_audio
speakers:
  host:
    display_name: 大牛
    voice_id: minimax:cn_female_002
    default_style: calm
  guest:
    display_name: 一帆
    voice_id: minimax:cn_male_001
    default_style: informative
defaults:
  tts:
    format: wav
    sample_rate: 44100
---

## Slide 01 | AgentFlow 简介
- speaker: host
  text: |
    欢迎大家来到今天的午餐分享。我是大牛。
    今天我们来聊聊 Stanford 最新的 AgentFlow 框架——一个让智能体“边工作边变聪明”的系统。
- speaker: guest
  text: |
    没错，这篇论文的全名是 “In-the-Flow Agentic System Optimization for Effective Planning and Tool Use”。
    它把智能体的四个核心角色——Planner、Executor、Verifier 和 Generator——整合进一个可训练的循环系统。
    最厉害的是，它在执行过程中使用强化学习，也就是所谓的 in-the-flow 优化。

## Slide 02 | 从 Prompt 到 Agentic Systems
- speaker: host
  text: |
    一帆，我记得以前我们都是靠 prompt 来控制模型行为。
    为什么后来大家开始讲“Agentic System”？
- speaker: guest
  text: |
    这是个自然演进。
    2023 年我们还在做 Prompt Engineering；
    到了 2024 年，有了 ReAct、AutoGPT 这种能思考、能调用工具的 LLM；
    现在 2025 年，AgentFlow 代表新阶段——它让 agent 不再是剧本式执行，而是能通过在线强化学习自己改进。

## Slide 03 | 问题定义
- speaker: host
  text: |
    听起来不错，但到底要解决什么问题？
- speaker: guest
  text: |
    两个痛点。
    第一，传统 LLM 在长任务链上训练不稳定；
    第二，多工具协作下泛化性差。
    大模型往往靠一个庞大的策略同时规划、调用工具、生成输出，这在长 horizon 下会崩溃。
    AgentFlow 把任务拆成模块，让系统能稳定学习、动态适应环境。

## Slide 04 | AgentFlow 架构概览
- speaker: host
  text: |
    说到模块，你刚提到四个角色：Planner、Executor、Verifier、Generator。
    能再展开说说吗？
- speaker: guest
  text: |
    当然。
    Planner 规划子目标并选择工具；
    Executor 调用具体工具执行；
    Verifier 检查结果是否满足目标；
    Generator 生成最终答案。
    他们通过共享的 Memory 和 Toolset 协作，就像一个团队在迭代完成任务。

## Slide 05 | Memory 与 Toolset
- speaker: host
  text: |
    Memory 听起来很关键，它存什么？
- speaker: guest
  text: |
    它是一个可进化的结构化记录：每一轮的子任务、工具调用结果、验证状态。
    比如，在多轮问答中，Memory 就像日志，把 reasoning 过程显性化。
    Toolset 则是工具库——可以是 Google Search、Python Coder、Web Search 等。
    这两个组件让 AgentFlow 有“长期记忆”和“工具意识”。

## Slide 06 | 数学形式化
- speaker: host
  text: |
    我知道论文里把它建模成 MDP，对吗？
- speaker: guest
  text: |
    对，整个过程是一个多回合 Markov Decision Process。
    在每个时刻 t，状态是 (q, K, Mᵗ)，Planner 根据策略 πθ 选动作 aᵗ。
    Executor 和 Verifier 给出结果 eᵗ、vᵗ，然后更新 Memory。
    当 Verifier 判断完成时，Generator 生成最终答案。
    这样整个流程就能被强化学习优化。

## Slide 07 | Flow-GRPO 训练算法
- speaker: host
  text: |
    那 Flow-GRPO 又是什么？
- speaker: guest
  text: |
    Flow-GRPO 全称是 Flow-based Group Refined Policy Optimization。
    它把长时序、多回合的稀疏奖励问题，转成一系列可处理的单回合更新。
    论文第 3 页的图四展示了整个流程——奖励在每次 rollout 后广播给所有步骤，
    让局部决策和最终成功对齐。

## Slide 08 | 数学核心
- speaker: host
  text: |
    有没有公式能帮助理解？
- speaker: guest
  text: |
    有，他们定义了目标函数：
    L(θ) 等于每回合期望的 min(rₜ·Aₜ, clip(rₜ,1−ε,1+ε)·Aₜ)，
    其中 Aₜ 是 Advantage。
    不同于传统 RL，这里每一步都共享相同的 trajectory-level 奖励。
    再加上 Group Normalization 稳定训练，就能实现 in-the-flow 的学习。

## Slide 09 | 实验结果
- speaker: host
  text: |
    论文里结果非常亮眼，我记得他们用的是 Qwen2.5-7B 模型？
- speaker: guest
  text: |
    对，只训练 Planner，其他模块固定。
    在 10 个 benchmark 上平均提升 14% 到 15%，
    包括 search、agentic reasoning、数学和科学任务。
    最惊人的是，它甚至在多个任务上超过了 GPT-4o。

## Slide 10 | 对比分析
- speaker: host
  text: |
    它到底比谁强？ReAct？AutoGen？
- speaker: guest
  text: |
    是的。表一和表二显示，
    相比 AutoGen、ToRL、TIR 等模型，
    AgentFlow 在 search 提升 14.9%，math 提升 14.5%。
    因为它不是静态 prompt，而是有 RL 优化的 planner。
    简单说：它能学会“什么时候用哪个工具”。

## Slide 11 | 工具调用优化
- speaker: host
  text: |
    我看到论文第 8 页的图 5，好像展示了工具使用的变化？
- speaker: guest
  text: |
    对，非常有意思。
    在 2Wiki 数据集上，Google Search 使用率上升 42%；
    而在 MedQA 医学任务上，它反而减少泛用搜索，转向 Wikipedia 与 Web Search。
    说明 Planner 学会根据任务类型选择最合适的工具，而不再乱用。

## Slide 12 | Flow-GRPO 的稳定性
- speaker: host
  text: |
    那训练是不是也更稳？
- speaker: guest
  text: |
    是的。论文图 6 显示工具调用错误率下降近 30%，
    而且 reward 曲线平滑上升，response 更简洁。
    Flow-GRPO 比 ToRL 等传统强化学习高效且稳定。

## Slide 13 | 规模与扩展性
- speaker: host
  text: |
    如果模型变大，或推理回合变多，会怎样？
- speaker: guest
  text: |
    他们实验了从 3B 到 7B 的 Qwen2.5；
    无论规模大小，Flow-GRPO 都带来稳定收益。
    同时，允许更多推理回合 Tmax 从 3 到 10，准确率也持续提升。
    表明系统能自适应任务复杂度，充分利用更长的思考时间。

## Slide 14 | 相关工作
- speaker: host
  text: |
    它和以前的 ToRL、ReSearch、AutoGen 有什么根本不同？
- speaker: guest
  text: |
    以前的都是单体模型：一个 policy 同时思考和调用工具；
    而 AgentFlow 是多模块协作，每个模块有角色、有记忆。
    更重要的是，它能“在线学习”，不依赖静态数据或手工规则。

## Slide 15 | 结论
- speaker: host
  text: |
    那我们可以怎么总结这篇论文？
- speaker: guest
  text: |
    三个贡献。
    一，提出一个可训练的 in-the-flow agentic 框架；
    二，提出 Flow-GRPO，让多回合任务的 RL 成为可解问题；
    三，通过十个 benchmark 证明它超越了所有 baseline，包括 GPT-4o。
    简言之——AgentFlow 让智能体真的学会“边干边学”。

## Slide 16 | 对工程团队的启示
- speaker: host
  text: |
    这些听上去很学术，我们能用在自己项目吗？
- speaker: guest
  text: |
    完全可以。
    比如我们 LLM API Gateway 项目想做一个 SWE Agent，
    就能借鉴 AgentFlow 的结构。
    Planner 决定子任务，Executor 调用代码生成或部署工具，
    Verifier 检查测试是否通过，Memory 记录上下文。
    未来我们甚至可以用 Flow-GRPO 来让 Agent 学习更高效的 DevOps 流程。

## Slide 17 | 实施路线图
- speaker: host
  text: |
    如果真要落地，第一步该做什么？
- speaker: guest
  text: |
    第一步，定义工具封装；
    第二步，写 Verifier；
    第三步，收集执行日志；
    有了轨迹数据，我们就能模拟 Flow-GRPO 的 RL 训练。
    起步可以先用 prompt-based Planner，再逐步引入 RL。
    目标是让系统学会自主调度工具，而不是靠人工指令。

## Slide 18 | 挑战与思考
- speaker: host
  text: |
    现实中会遇到哪些坑？
- speaker: guest
  text: |
    奖励设计最难，怎样定义“成功”要靠工程可验证指标；
    其次是安全问题——执行代码要 sandbox；
    还有 memory 管理，长任务的上下文可能爆炸。
    不过这些挑战都在可控范围内。

## Slide 19 | 未来方向
- speaker: host
  text: |
    你觉得未来几年 AgentFlow 会往哪里走？
- speaker: guest
  text: |
    作者也提到下一步要扩展到其他模块的训练，不只 Planner；
    还要引入更细粒度的奖励和更复杂的任务环境。
    长远看，AgentFlow 会成为一种通用的“可持续学习智能体”框架，
    让 agent 在真实世界持续改进，而不是一劳永逸。

## Slide 20 | 结语
- speaker: host
  text: |
    今天我们从 Prompt 的年代一路讲到可训练智能体。
    AgentFlow 让我们看到 AI 可以在工作流中自我优化的未来。
- speaker: guest
  text: |
    没错，正如论文最后一句话说的：
    “In-the-Flow optimization enables robust planning and reliable tool use.”
    谢谢大家收听，也期待我们能在自己的系统里实现类似的 AgentFlow。


"""Multi-agent compliance review orchestra."""

import os
import json
from dataclasses import dataclass, field
from typing import AsyncGenerator, Literal

from openai import AsyncOpenAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


@dataclass
class AgentRole:
    """Definition of an agent role in the compliance orchestra."""

    role_id: str
    name: str
    description: str
    focus_areas: list[str]
    perspective: str


@dataclass
class AgentOutput:
    """Output from a single agent review."""

    role_id: str
    role_name: str
    findings: list[dict]
    risk_assessment: str
    recommendations: list[str]
    confidence_level: Literal["high", "medium", "low"]
    evidence_gaps: list[str]


# Define agent roles
REGULATORY_AUDITOR = AgentRole(
    role_id="regulatory_auditor",
    name="法规审核员",
    description="模拟政府/外部审核员视角，关注法规要求、强证据、缺口",
    focus_areas=["法规符合性", "强制性要求", "监管风险", "处罚后果"],
    perspective="从外部监管机构的角度审查，关注是否满足法规最低要求，识别可能导致监管处罚的风险",
)

INTERNAL_QMS_AUDITOR = AgentRole(
    role_id="internal_qms_auditor",
    name="内部QMS审核员",
    description="关注程序文件、记录、DHR、CAPA、培训、内审等内部证据",
    focus_areas=["程序完整性", "记录可追溯性", "流程执行", "培训有效性"],
    perspective="从内部质量管理体系的角度审查，关注流程是否完整、记录是否充分、执行是否到位",
)

RISK_REVIEWER = AgentRole(
    role_id="risk_reviewer",
    name="风险评审员",
    description="关注风险管理和产品安全相关要求",
    focus_areas=["风险控制", "产品安全", "患者安全", "风险收益分析"],
    perspective="从风险管理的角度审查，关注措施是否充分控制风险、是否影响产品安全性和有效性",
)


async def run_agent_review(
    role: AgentRole,
    clause_text: str,
    evidence: str,
    api_key: str,
    base_url: str,
) -> AgentOutput:
    """Run a single agent review."""

    system_prompt = f"""你是一个专业的合规审核助手，扮演{role.name}角色。

你的职责：{role.description}

你的审查视角：{role.perspective}

你需要关注的重点领域：
{chr(10).join(f'- {area}' for area in role.focus_areas)}

请用中文回答，输出JSON格式的结果。
"""

    user_prompt = f"""请从你的专业角度审查以下条款和证据：

## 审查条款
{clause_text}

## 可用证据
{evidence}

请输出以下JSON格式的结果：
{{
    "findings": [
        {{
            "area": "关注领域",
            "status": "符合/需澄清/缺乏证据/未提及",
            "description": "发现描述",
            "evidence_ref": "引用的证据"
        }}
    ],
    "risk_assessment": "风险评估（低/中/高）及说明",
    "recommendations": ["建议1", "建议2"],
    "confidence_level": "high/medium/low",
    "evidence_gaps": ["证据缺口1", "证据缺口2"]
}}
"""

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    model = ChatOpenAI(
        model="mimo-v2.5-pro",
        max_tokens=2000,
        client=client,
    )

    response = await model.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ])

    # Parse response
    import json
    try:
        # Try to extract JSON from response
        content = response.content
        # Find JSON block
        start = content.find('{')
        end = content.rfind('}') + 1
        if start >= 0 and end > start:
            result = json.loads(content[start:end])
        else:
            result = {}
    except Exception:
        result = {}

    return AgentOutput(
        role_id=role.role_id,
        role_name=role.name,
        findings=result.get("findings", []),
        risk_assessment=result.get("risk_assessment", "未评估"),
        recommendations=result.get("recommendations", []),
        confidence_level=result.get("confidence_level", "medium"),
        evidence_gaps=result.get("evidence_gaps", []),
    )


async def run_director_review(
    clause_text: str,
    agent_outputs: list[AgentOutput],
    api_key: str,
    base_url: str,
) -> str:
    """Run the Audit Director to synthesize all agent outputs."""

    # Format agent outputs
    agent_summaries = []
    for output in agent_outputs:
        findings_str = "\n".join(
            f"  - {f.get('area', '未知')}: {f.get('status', '未知')} - {f.get('description', '无描述')}"
            for f in output.findings
        )
        agent_summaries.append(f"""
### {output.role_name}
**发现：**
{findings_str}
**风险评估：** {output.risk_assessment}
**建议：** {', '.join(output.recommendations)}
**信心水平：** {output.confidence_level}
**证据缺口：** {', '.join(output.evidence_gaps) if output.evidence_gaps else '无'}
""")

    agents_review = "\n".join(agent_summaries)

    system_prompt = """你是审计总监（Audit Director），负责汇总多位审核员的发现，生成最终的合规审查报告。

你的职责：
1. 综合各位审核员的发现
2. 识别共识和分歧
3. 评估总体风险等级
4. 生成结构化的最终报告
5. 确保所有结论都有证据支持

请用中文输出专业的审查报告。
"""

    user_prompt = f"""请根据以下条款和多位审核员的发现，生成最终的合规审查报告：

## 审查条款
{clause_text}

## 各审核员发现
{agents_review}

请生成包含以下部分的审查报告：
1. 审查概述
2. 条款要求摘要
3. 综合发现（按子条款组织）
4. 风险评估与分级
5. 改进建议（按优先级排序）
6. 证据缺口与后续行动
7. 结论

请确保报告专业、结构清晰、建议可操作。
"""

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    model = ChatOpenAI(
        model="mimo-v2.5-pro",
        max_tokens=4000,
        client=client,
    )

    response = await model.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ])

    return response.content


# ============================================================
# Streaming variants
# ============================================================

async def run_agent_review_streaming(
    role: AgentRole,
    clause_text: str,
    evidence: str,
    api_key: str,
    base_url: str,
) -> AsyncGenerator[dict, None]:
    """Run a single agent review with streaming output.

    Yields dicts:
    - {"type": "text", "content": str}  -- incremental text chunk
    - {"type": "complete", "output": AgentOutput}  -- final result
    """

    system_prompt = f"""你是一个专业的合规审核助手，扮演{role.name}角色。

你的职责：{role.description}

你的审查视角：{role.perspective}

你需要关注的重点领域：
{chr(10).join(f'- {area}' for area in role.focus_areas)}

请用中文回答，输出JSON格式的结果。
"""

    user_prompt = f"""请从你的专业角度审查以下条款和证据：

## 审查条款
{clause_text}

## 可用证据
{evidence}

请输出以下JSON格式的结果：
{{
    "findings": [
        {{
            "area": "关注领域",
            "status": "符合/需澄清/缺乏证据/未提及",
            "description": "发现描述",
            "evidence_ref": "引用的证据"
        }}
    ],
    "risk_assessment": "风险评估（低/中/高）及说明",
    "recommendations": ["建议1", "建议2"],
    "confidence_level": "high/medium/low",
    "evidence_gaps": ["证据缺口1", "证据缺口2"]
}}
"""

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    model = ChatOpenAI(
        model="mimo-v2.5-pro",
        max_tokens=2000,
        client=client,
    )

    full_content = ""
    async for event in model.astream_events(
        [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)],
        version="v2",
    ):
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            if chunk.content:
                full_content += chunk.content
                yield {"type": "text", "content": chunk.content}

    # Parse the complete response
    try:
        start = full_content.find('{')
        end = full_content.rfind('}') + 1
        if start >= 0 and end > start:
            result = json.loads(full_content[start:end])
        else:
            result = {}
    except Exception:
        result = {}

    yield {
        "type": "complete",
        "output": AgentOutput(
            role_id=role.role_id,
            role_name=role.name,
            findings=result.get("findings", []),
            risk_assessment=result.get("risk_assessment", "未评估"),
            recommendations=result.get("recommendations", []),
            confidence_level=result.get("confidence_level", "medium"),
            evidence_gaps=result.get("evidence_gaps", []),
        ),
    }


async def run_director_review_streaming(
    clause_text: str,
    agent_outputs: list[AgentOutput],
    api_key: str,
    base_url: str,
) -> AsyncGenerator[dict, None]:
    """Run the Audit Director with streaming output.

    Yields dicts:
    - {"type": "text", "content": str}  -- incremental text chunk
    - {"type": "complete", "report": str}  -- final report
    """

    agent_summaries = []
    for output in agent_outputs:
        findings_str = "\n".join(
            f"  - {f.get('area', '未知')}: {f.get('status', '未知')} - {f.get('description', '无描述')}"
            for f in output.findings
        )
        agent_summaries.append(f"""
### {output.role_name}
**发现：**
{findings_str}
**风险评估：** {output.risk_assessment}
**建议：** {', '.join(output.recommendations)}
**信心水平：** {output.confidence_level}
**证据缺口：** {', '.join(output.evidence_gaps) if output.evidence_gaps else '无'}
""")

    agents_review = "\n".join(agent_summaries)

    system_prompt = """你是审计总监（Audit Director），负责汇总多位审核员的发现，生成最终的合规审查报告。

你的职责：
1. 综合各位审核员的发现
2. 识别共识和分歧
3. 评估总体风险等级
4. 生成结构化的最终报告
5. 确保所有结论都有证据支持

请用中文输出专业的审查报告。
"""

    user_prompt = f"""请根据以下条款和多位审核员的发现，生成最终的合规审查报告：

## 审查条款
{clause_text}

## 各审核员发现
{agents_review}

请生成包含以下部分的审查报告：
1. 审查概述
2. 条款要求摘要
3. 综合发现（按子条款组织）
4. 风险评估与分级
5. 改进建议（按优先级排序）
6. 证据缺口与后续行动
7. 结论

请确保报告专业、结构清晰、建议可操作。
"""

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    model = ChatOpenAI(
        model="mimo-v2.5-pro",
        max_tokens=4000,
        client=client,
    )

    full_content = ""
    async for event in model.astream_events(
        [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)],
        version="v2",
    ):
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            if chunk.content:
                full_content += chunk.content
                yield {"type": "text", "content": chunk.content}

    yield {"type": "complete", "report": full_content}

"""Test script — isolated node testing."""
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")
os.chdir(r"d:\ai-agent-mkt")

from src.models.trace import RunTrace


def test_brief_parser():
    print("=" * 60)
    print("TEST 1: brief_parser_node")
    print("=" * 60)
    from src.nodes.brief_parser import brief_parser_node

    state = {
        "raw_input": "Tao campaign awareness cho dich vu xem tu vi online, target Gen Z quan tam tam linh. Channels: Facebook va Instagram.",
        "trace": RunTrace(),
    }

    result = brief_parser_node(state)

    if result.get("error"):
        print(f"ERROR: {result['error']}")
        return False

    brief = result["brief"]
    print(f"  Goal: {brief.goal.value}")
    print(f"  Brand: {brief.brand.name}")
    print(f"  Audience: {brief.audience.persona_description}")
    print(f"  Product: {brief.offer.product_or_service}")
    print(f"  Channels: {[c.value for c in brief.channels]}")
    print(f"  Deliverables: {[d.value for d in brief.deliverables]}")
    print(f"  Awareness Stage: {brief.audience.awareness_stage.value}")
    print(">>> BRIEF PARSER: PASSED <<<")
    return True


def test_context_builder(brief=None):
    print("\n" + "=" * 60)
    print("TEST 2: context_builder_node")
    print("=" * 60)
    from src.nodes.context_builder import context_builder_node
    from src.models.brief import (
        CampaignBrief, CampaignGoal, BrandSpec, AudienceSpec,
        OfferSpec, Channel, Deliverable,
    )

    if brief is None:
        brief = CampaignBrief(
            goal=CampaignGoal.AWARENESS,
            brand=BrandSpec(name="TuViOnline"),
            audience=AudienceSpec(persona_description="Gen Z quan tam tam linh"),
            offer=OfferSpec(
                product_or_service="Dich vu xem tu vi online",
                key_message="Kham pha ban than qua la so tu vi",
                cta="Dat lich xem tu vi",
            ),
            channels=[Channel.FACEBOOK, Channel.INSTAGRAM],
            deliverables=[Deliverable.POST, Deliverable.CAROUSEL],
        )

    state = {"brief": brief, "trace": RunTrace()}
    result = context_builder_node(state)

    if result.get("error"):
        print(f"ERROR: {result['error']}")
        return None

    ctx = result["context_pack"]
    for key, val in ctx.items():
        if isinstance(val, str):
            print(f"  {key}: {len(val)} chars")
        elif isinstance(val, dict):
            print(f"  {key}: {list(val.keys())}")
        else:
            print(f"  {key}: {type(val).__name__}")
    print(">>> CONTEXT BUILDER: PASSED <<<")
    return ctx


def test_strategist(brief=None, context_pack=None):
    print("\n" + "=" * 60)
    print("TEST 3: strategist_node")
    print("=" * 60)
    from src.nodes.strategist import strategist_node
    from src.models.brief import (
        CampaignBrief, CampaignGoal, BrandSpec, AudienceSpec,
        OfferSpec, Channel, Deliverable,
    )

    if brief is None:
        brief = CampaignBrief(
            goal=CampaignGoal.AWARENESS,
            brand=BrandSpec(name="TuViOnline"),
            audience=AudienceSpec(persona_description="Gen Z quan tam tam linh"),
            offer=OfferSpec(
                product_or_service="Dich vu xem tu vi online",
                key_message="Kham pha ban than qua la so tu vi",
                cta="Dat lich xem tu vi",
            ),
            channels=[Channel.FACEBOOK, Channel.INSTAGRAM],
            deliverables=[Deliverable.POST, Deliverable.CAROUSEL],
        )

    if context_pack is None:
        from src.nodes.context_builder import context_builder_node
        ctx_result = context_builder_node({"brief": brief, "trace": RunTrace()})
        context_pack = ctx_result["context_pack"]

    state = {"brief": brief, "context_pack": context_pack, "trace": RunTrace()}
    result = strategist_node(state)

    if result.get("error"):
        print(f"ERROR: {result['error']}")
        return None

    strategy = result["strategy"]
    print(f"  Strategy length: {len(strategy)} chars")
    print(f"  First 300 chars:\n{strategy[:300]}...")
    print(">>> STRATEGIST: PASSED <<<")
    return strategy


def test_message_architect(brief=None, context_pack=None, strategy=None):
    print("\n" + "=" * 60)
    print("TEST 4: message_architect_node")
    print("=" * 60)
    from src.nodes.message_architect import message_architect_node
    from src.models.brief import (
        CampaignBrief, CampaignGoal, BrandSpec, AudienceSpec,
        OfferSpec, Channel, Deliverable,
    )

    if brief is None:
        brief = CampaignBrief(
            goal=CampaignGoal.AWARENESS,
            brand=BrandSpec(name="TuViOnline"),
            audience=AudienceSpec(persona_description="Gen Z quan tam tam linh"),
            offer=OfferSpec(
                product_or_service="Dich vu xem tu vi online",
                key_message="Kham pha ban than qua la so tu vi",
                cta="Dat lich xem tu vi",
            ),
            channels=[Channel.FACEBOOK, Channel.INSTAGRAM],
            deliverables=[Deliverable.POST, Deliverable.CAROUSEL],
        )

    if context_pack is None:
        from src.nodes.context_builder import context_builder_node
        ctx_result = context_builder_node({"brief": brief, "trace": RunTrace()})
        context_pack = ctx_result["context_pack"]

    if strategy is None:
        strategy = "Sample strategy for testing message architect."

    state = {
        "brief": brief,
        "context_pack": context_pack,
        "strategy": strategy,
        "review_result": None,
        "trace": RunTrace(),
    }
    result = message_architect_node(state)

    if result.get("error"):
        print(f"ERROR: {result['error']}")
        return None

    mm = result["master_message"]
    print(f"  Core promise: {mm.core_promise}")
    print(f"  Key points: {mm.key_points}")
    print(f"  Emotional angle: {mm.emotional_angle}")
    print(f"  CTA: {mm.cta_primary}")
    print(f"  Tone: {mm.tone_direction}")
    print(">>> MESSAGE ARCHITECT: PASSED <<<")
    return mm


if __name__ == "__main__":
    import sys
    test_name = sys.argv[1] if len(sys.argv) > 1 else "brief_parser"

    if test_name == "brief_parser":
        test_brief_parser()
    elif test_name == "context_builder":
        test_context_builder()
    elif test_name == "strategist":
        test_strategist()
    elif test_name == "message_architect":
        test_message_architect()
    elif test_name == "all":
        ok = test_brief_parser()
        if ok:
            ctx = test_context_builder()
            if ctx:
                strategy = test_strategist(context_pack=ctx)
                if strategy:
                    test_message_architect(strategy=strategy, context_pack=ctx)
    else:
        print(f"Unknown test: {test_name}")
        print("Available: brief_parser, context_builder, strategist, message_architect, all")

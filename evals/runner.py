"""
Chạy eval và in kết quả.

    python -m evals.runner --tier retrieval          # miễn phí, chạy trong CI
    python -m evals.runner --tier generation         # gọi API thật, tốn tiền
    python -m evals.runner --tier retrieval --baseline evals/baseline/retrieval.json
    python -m evals.runner --tier retrieval --save-baseline

Vì sao tách khỏi pytest: tầng generation tốn tiền và chậm. Để lẫn vào pytest
thì hoặc chạy nhầm trong CI, hoặc bị skip mãi rồi mục rữa. Tách hẳn ra thì mỗi
lần chạy là một quyết định có ý thức.
"""
import argparse
import json
import shutil
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Optional

import yaml

from evals import checks

EVALS_DIR = Path(__file__).resolve().parent
CASES_DIR = EVALS_DIR / "cases"
BRANDS_DIR = EVALS_DIR / "brands"
BASELINE_DIR = EVALS_DIR / "baseline"


def nap_cases(loc: Optional[str] = None) -> list[dict]:
    cases = []
    for f in sorted(CASES_DIR.glob("*.yaml")):
        case = yaml.safe_load(f.read_text(encoding="utf-8"))
        case["_file"] = f.name
        if loc and loc not in case["id"]:
            continue
        cases.append(case)
    return cases


class KhoBrandTam:
    """
    Dựng một knowledge_base tạm từ evals/brands.

    Cố ý KHÔNG dùng knowledge_base thật: kết quả eval phải ổn định, không đổi
    khi ai đó sửa dữ liệu thật. Đây cũng là chỗ nhét tài liệu injection vào mà
    không làm bẩn repo.
    """

    def __init__(self, case: dict):
        self.case = case
        self.tmp: Optional[Path] = None

    def __enter__(self) -> Path:
        self.tmp = Path(tempfile.mkdtemp(prefix="eval_kb_"))
        kb = self.tmp / "knowledge_base"
        (kb / "_global" / "platforms").mkdir(parents=True)
        (kb / "_global" / "policies").mkdir(parents=True)

        # Dùng lại luật nền tảng và quy định chung THẬT — chúng ổn định và là
        # một phần của thứ đang được đo
        that = Path(__file__).resolve().parent.parent / "knowledge_base" / "_global"
        for phan in ("platforms", "policies"):
            nguon = that / phan
            if nguon.exists():
                for f in nguon.glob("*.md"):
                    shutil.copy2(f, kb / "_global" / phan / f.name)

        brands = kb / "brands"
        brands.mkdir()
        if self.case.get("brand"):
            shutil.copytree(BRANDS_DIR / self.case["brand"], brands / self.case["brand"])

            inject = self.case.get("inject_document")
            if inject:
                dich = brands / self.case["brand"] / inject["path"]
                dich.parent.mkdir(parents=True, exist_ok=True)
                dich.write_text(inject["content"], encoding="utf-8")

        return kb

    def __exit__(self, *a):
        if self.tmp:
            shutil.rmtree(self.tmp, ignore_errors=True)


def _tro_retriever_vao(kb: Path):
    """Trỏ retriever sang kho tạm. Trả về hàm khôi phục."""
    import src.knowledge.retriever as rt

    cu = (rt.KNOWLEDGE_DIR, rt.BRANDS_DIR, rt.GLOBAL_DIR)
    rt.KNOWLEDGE_DIR = kb
    rt.BRANDS_DIR = kb / "brands"
    rt.GLOBAL_DIR = kb / "_global"
    rt._read_file_cached.cache_clear()

    def khoi_phuc():
        rt.KNOWLEDGE_DIR, rt.BRANDS_DIR, rt.GLOBAL_DIR = cu
        rt._read_file_cached.cache_clear()

    return khoi_phuc


def chay_retrieval(case: dict) -> dict:
    """
    Tầng 1: dựng context và chấm. KHÔNG gọi LLM.

    Brief được dựng thủ công từ case thay vì qua brief_parser (vốn cần LLM) —
    thứ đang đo ở đây là retriever, không phải parser.
    """
    from src.models.brief import (
        AudienceSpec,
        BrandSpec,
        CampaignBrief,
        CampaignGoal,
        Channel,
        Deliverable,
        OfferSpec,
    )

    with KhoBrandTam(case) as kb:
        khoi_phuc = _tro_retriever_vao(kb)
        try:
            import src.knowledge.retriever as rt

            raw = case["brief"]["raw_input"]
            brief = CampaignBrief(
                goal=CampaignGoal.AWARENESS,
                brand=BrandSpec(name=""),
                audience=AudienceSpec(persona_description=raw),
                offer=OfferSpec(product_or_service=raw, key_message=raw, cta="tìm hiểu thêm"),
                channels=[Channel.FACEBOOK],
                deliverables=[Deliverable.POST],
            )
            ctx = rt.build_context_pack(brief, brand_id=case.get("brand"))
        finally:
            khoi_phuc()

    ket_qua = checks.chay_kiem_retrieval(ctx, case.get("expect", {}))
    return {
        "id": case["id"],
        "tier": "retrieval",
        "checks": [asdict(r) for r in ket_qua],
        **checks.tom_tat(ket_qua),
    }


def chay_generation(case: dict) -> dict:
    """
    Tầng 2: chạy pipeline thật rồi chấm nội dung sinh ra. TỐN TIỀN.
    """
    from api.pipeline_runner import PipelineRunner

    with KhoBrandTam(case) as kb:
        khoi_phuc = _tro_retriever_vao(kb)
        try:
            import src.knowledge.brand_manager as bm

            bm_cu = bm.BRANDS_DIR
            bm.BRANDS_DIR = kb / "brands"
            try:
                runner = PipelineRunner()
                runner.phase_1_parse(case["brief"]["raw_input"], brand_id=case.get("brand"))
                if runner.state.get("error"):
                    return _that_bai(case, runner.state["error"])

                runner.phase_2_strategy()
                if runner.state.get("error"):
                    return _that_bai(case, runner.state["error"])

                runner.phase_3_content()
                if runner.state.get("error"):
                    return _that_bai(case, runner.state["error"])
            finally:
                bm.BRANDS_DIR = bm_cu
        finally:
            khoi_phuc()

    content = runner.state.get("campaign_content")
    text = "\n\n".join(
        " ".join(filter(None, [p.hook, p.body, p.cta_text, " ".join(p.hashtags)]))
        for p in (content.pieces if content else [])
    )

    ket_qua = checks.chay_kiem_noi_dung(text, case.get("expect", {}))
    return {
        "id": case["id"],
        "tier": "generation",
        "checks": [asdict(r) for r in ket_qua],
        "cost": round(runner.state["trace"].total_cost_estimate, 4),
        "text_preview": text[:400],
        **checks.tom_tat(ket_qua),
    }


def _that_bai(case: dict, loi: str) -> dict:
    return {
        "id": case["id"],
        "tier": "generation",
        "checks": [],
        "passed": 0,
        "total": 1,
        "ok": False,
        "failed": ["pipeline_error"],
        "error": loi,
    }


def in_bang(ket_qua: list[dict]) -> None:
    print()
    print(f"{'CASE':<32} {'ĐẠT':>8}  CHI TIẾT")
    print("-" * 78)
    for r in ket_qua:
        # Case không có phép kiểm nào cho tầng này thì là BỎ QUA, không phải ĐẠT.
        # Hiện 0/0 PASS là nói dối rằng nó đã được kiểm.
        if r["total"] == 0:
            dau = "SKIP"
        else:
            dau = "PASS" if r["ok"] else "FAIL"
        chi_tiet = ", ".join(r["failed"]) if r["failed"] else ""
        if r.get("error"):
            chi_tiet = f"pipeline lỗi: {r['error'][:40]}"
        print(f"{r['id']:<32} {r['passed']}/{r['total']} {dau:>4}  {chi_tiet}")

    co_kiem = [r for r in ket_qua if r["total"] > 0]
    dat = sum(1 for r in co_kiem if r["ok"])
    bo_qua = len(ket_qua) - len(co_kiem)
    print("-" * 78)
    print(f"{dat}/{len(co_kiem)} case đạt" + (f", {bo_qua} bỏ qua ở tầng này" if bo_qua else ""))

    tien = sum(r.get("cost", 0) for r in ket_qua)
    if tien:
        print(f"Chi phí lần chạy này: ~${tien:.4f}")


def so_voi_moc(ket_qua: list[dict], baseline_path: Path) -> bool:
    """
    So với lần chạy trước. Trả về False nếu có hồi quy.

    Đây là thứ biến eval từ "một lần chạy cho vui" thành cổng chặn: chỉ số tụt
    so với mốc là có chuyện, dù test đơn vị vẫn xanh.
    """
    if not baseline_path.exists():
        print(f"\nChưa có mốc ở {baseline_path} — chạy với --save-baseline để tạo.")
        return True

    moc = {r["id"]: r for r in json.loads(baseline_path.read_text(encoding="utf-8"))}
    hoi_quy = []

    print("\nSo với mốc:")
    for r in ket_qua:
        cu = moc.get(r["id"])
        if not cu:
            print(f"  {r['id']}: case mới")
            continue
        if cu["passed"] > r["passed"]:
            hoi_quy.append(r["id"])
            print(f"  {r['id']}: TỤT {cu['passed']} -> {r['passed']}")
        elif cu["passed"] < r["passed"]:
            print(f"  {r['id']}: tốt lên {cu['passed']} -> {r['passed']}")

    mat_case = set(moc) - {r["id"] for r in ket_qua}
    if mat_case:
        print(f"  Case biến mất khỏi lần chạy này: {', '.join(sorted(mat_case))}")

    if hoi_quy:
        print(f"\nHỒI QUY ở {len(hoi_quy)} case: {', '.join(hoi_quy)}")
        return False

    print("  Không có hồi quy.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Chạy eval chất lượng AI")
    parser.add_argument("--tier", choices=["retrieval", "generation"], default="retrieval")
    parser.add_argument("--case", help="Chỉ chạy case có id chứa chuỗi này")
    parser.add_argument("--baseline", help="So với file mốc")
    parser.add_argument("--save-baseline", action="store_true", help="Ghi kết quả làm mốc")
    parser.add_argument("--yes", action="store_true", help="Bỏ qua hỏi xác nhận chi phí")
    args = parser.parse_args()

    from src.utils.logging_config import setup_logging

    setup_logging("WARNING")

    cases = nap_cases(args.case)
    if not cases:
        print("Không có case nào.")
        return 1

    if args.tier == "generation" and not args.yes:
        print(f"Sắp chạy {len(cases)} case qua Anthropic API. Mỗi case tốn khoảng $0.05-0.15.")
        if input("Chạy tiếp? [y/N] ").strip().lower() not in ("y", "yes"):
            print("Đã huỷ.")
            return 0

    chay = chay_retrieval if args.tier == "retrieval" else chay_generation
    ket_qua = []
    for case in cases:
        print(f"  đang chạy {case['id']}...", flush=True)
        ket_qua.append(chay(case))

    in_bang(ket_qua)

    if args.save_baseline:
        BASELINE_DIR.mkdir(parents=True, exist_ok=True)
        dich = BASELINE_DIR / f"{args.tier}.json"
        dich.write_text(json.dumps(ket_qua, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nĐã ghi mốc: {dich}")
        return 0

    khong_hoi_quy = True
    if args.baseline:
        khong_hoi_quy = so_voi_moc(ket_qua, Path(args.baseline))

    tat_ca_dat = all(r["ok"] for r in ket_qua if r["total"] > 0)
    return 0 if (tat_ca_dat and khong_hoi_quy) else 1


if __name__ == "__main__":
    sys.exit(main())

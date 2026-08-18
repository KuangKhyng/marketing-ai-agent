"""
Canh cho ba nơi khai báo dependency không lệch nhau.

Repo có ba nguồn, mỗi nguồn một mục đích:
  requirements.txt  -> nixpacks CÀI THẬT trên Railway
  pyproject.toml    -> metadata package + extra dev
  uv.lock           -> pin chính xác cho môi trường dev local

Trước đây chúng đã lệch thật: requirements ghi `langgraph>=0.2` trong khi
uv.lock và venv là 1.1.8 — nhảy qua một major mà không ai biết.

Test này không bắt ba file phải giống nhau từng chữ, chỉ bắt chúng không được
nói ngược nhau.
"""
import tomllib
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.version import Version

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read_requirements() -> dict[str, Requirement]:
    reqs = {}
    for line in (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        req = Requirement(line)
        reqs[req.name.lower().replace("_", "-")] = req
    return reqs


def _read_pyproject_deps() -> dict[str, Requirement]:
    data = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    reqs = {}
    for spec in data["project"]["dependencies"]:
        req = Requirement(spec)
        reqs[req.name.lower().replace("_", "-")] = req
    return reqs


def _read_lock_versions() -> dict[str, str]:
    lock_path = PROJECT_ROOT / "uv.lock"
    if not lock_path.exists():
        pytest.skip("không có uv.lock")
    data = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    return {
        pkg["name"].lower().replace("_", "-"): pkg["version"]
        for pkg in data.get("package", [])
        if "version" in pkg
    }


def test_requirements_va_pyproject_khong_noi_nguoc_nhau():
    """
    Cùng một package thì hai file phải ghi cùng ràng buộc. Lệch nhau nghĩa là
    deploy và dev cài khác version.
    """
    reqs = _read_requirements()
    proj = _read_pyproject_deps()

    chung = set(reqs) & set(proj)
    assert chung, "Hai file không có package nào chung — chắc chắn có gì sai"

    lech = {
        name: (str(reqs[name].specifier), str(proj[name].specifier))
        for name in sorted(chung)
        if reqs[name].specifier != proj[name].specifier
    }
    assert not lech, f"Ràng buộc lệch nhau (requirements.txt vs pyproject): {lech}"


def test_pyproject_khong_thieu_package_nao_cua_requirements():
    """requirements.txt là thứ chạy thật; pyproject không được thiếu gì."""
    thieu = sorted(set(_read_requirements()) - set(_read_pyproject_deps()))
    assert not thieu, f"pyproject thiếu: {thieu}"


def test_version_trong_lock_thoa_man_requirements():
    """
    Đây là test bắt được lỗi cũ: requirements `>=0.2` mà lock là 1.1.8 thì
    ràng buộc vẫn thoả, nhưng nếu có chặn trên `<2` thì một ngày lock nhảy lên
    2.x là test đỏ ngay.
    """
    locked = _read_lock_versions()
    vi_pham = []

    for name, req in _read_requirements().items():
        if name not in locked:
            continue
        version = Version(locked[name])
        if not req.specifier.contains(version, prereleases=True):
            vi_pham.append(f"{name}: lock={version} không thoả {req.specifier}")

    assert not vi_pham, "uv.lock nói ngược requirements.txt:\n" + "\n".join(vi_pham)


def test_moi_package_deu_co_chan_tren():
    """
    Không có chặn trên thì mỗi lần deploy là một lần roulette version — đúng
    cách repo này đã trôi từ langgraph 0.2 lên 1.1.
    """
    thieu_chan = [
        name
        for name, req in _read_requirements().items()
        if not any(op in str(req.specifier) for op in ("<", "==", "~="))
    ]
    assert not thieu_chan, f"Thiếu chặn trên: {thieu_chan}"


def test_package_lock_co_binary_cho_linux():
    """
    package-lock.json phải chứa entry cài được cho linux/x64, nếu không CI và
    Railway build sẽ vỡ dù máy dev vẫn chạy tốt.

    Lỗi đã xảy ra: npm 10.1.0 trên Windows chỉ ghi entry của binary win32 vào
    `packages`; tên linux chỉ nằm trong danh sách optionalDependencies của
    rollup nên `npm ci` trên Linux không có gì để cài và báo lỗi rất khó hiểu
    ("Cannot find module @rollup/rollup-linux-x64-gnu"). Sinh lại lock bằng
    npm >= 11 thì đủ cả 25 platform.

    Nếu test này đỏ: cd web && npx npm@11 install --package-lock-only --include=dev
    """
    import json

    lock_path = PROJECT_ROOT / "web" / "package-lock.json"
    if not lock_path.exists():
        pytest.skip("chưa có web/package-lock.json")

    packages = json.loads(lock_path.read_text(encoding="utf-8")).get("packages", {})

    # Họ package nào có binary theo nền tảng thì phải có bản linux/x64
    linux_x64 = {
        key.split("node_modules/")[-1]
        for key, entry in packages.items()
        if "linux" in (entry.get("os") or []) and "x64" in (entry.get("cpu") or [])
    }

    can_co = {
        "@rollup/rollup-linux-x64-gnu": "vite build",
        "@esbuild/linux-x64": "vite dev/transform",
        "@tailwindcss/oxide-linux-x64-gnu": "tailwind v4",
        "lightningcss-linux-x64-gnu": "tailwind v4",
    }

    thieu = {name: ly_do for name, ly_do in can_co.items() if name not in linux_x64}
    assert not thieu, (
        "package-lock.json thiếu binary linux/x64 (npm ci trên CI/Railway sẽ vỡ): "
        f"{thieu}. Sinh lại: cd web && npx npm@11 install --package-lock-only --include=dev"
    )


def test_dep_dung_truc_tiep_deu_duoc_khai_bao():
    """
    anthropic và tenacity được import TRỰC TIẾP trong channel_renderer nhưng
    trước đây không khai báo ở đâu — chỉ tồn tại nhờ là transitive dep của
    langchain, tức là có thể biến mất sau một lần nâng version.
    """
    reqs = _read_requirements()
    source = (PROJECT_ROOT / "src" / "nodes" / "channel_renderer.py").read_text(
        encoding="utf-8"
    )

    for module in ("anthropic", "tenacity"):
        assert f"import {module}" in source or f"from {module}" in source, (
            f"{module} không còn được import — cập nhật test này"
        )
        assert module in reqs, f"{module} được import trực tiếp nhưng không khai báo"

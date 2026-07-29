"""GT既知のテストシーン生成（オフィス俯瞰の模式図・日本語ラベル付き）。

実写真の代わりに、違反状態を意図的に配置した模式図を描画する。
どのルールに違反しているかが構成上既知なので、パイプラインの
指摘再現率をGT付きで測れる（shokuba-lens開発の検証用）。
"""
from PIL import Image, ImageDraw, ImageFont

FONT = "/Volumes/GM71TB/model-foundry/invoice-gen/fonts/NotoSansJP.ttf"


def f(sz):
    return ImageFont.truetype(FONT, sz)


def scene_violations(path):
    """GT: aisle_clear違反・fire_equipment_access違反・cable_management違反 / stacking・deskは適合"""
    img = Image.new("RGB", (1000, 700), (245, 245, 240))
    d = ImageDraw.Draw(img)
    d.text((20, 15), "オフィス平面図（俯瞰）", font=f(26), fill=(30, 30, 30))
    # 通路（中央縦）
    d.rectangle([420, 60, 580, 680], outline=(150, 150, 150), width=3)
    d.text((445, 65), "通路（動線）", font=f(20), fill=(100, 100, 100))
    # 通路上の段ボール箱 → aisle_clear違反
    d.rectangle([460, 300, 550, 380], fill=(200, 160, 110), outline=(120, 90, 50), width=3)
    d.text((465, 325), "段ボール箱", font=f(18), fill=(60, 40, 10))
    # 消火器と、その前の椅子 → fire_equipment_access違反
    d.rectangle([880, 100, 960, 180], fill=(220, 60, 60))
    d.text((885, 125), "消火器", font=f(20), fill=(255, 255, 255))
    d.ellipse([860, 190, 950, 270], fill=(120, 120, 180))
    d.text((870, 218), "椅子", font=f(20), fill=(255, 255, 255))
    d.text((820, 275), "※消火器の前に椅子", font=f(16), fill=(120, 60, 60))
    # 床を横切るケーブル → cable_management違反
    d.line([(60, 600), (420, 560), (580, 540), (900, 500)], fill=(40, 40, 40), width=6)
    d.text((200, 610), "床を横切る電源ケーブル（カバーなし）", font=f(18), fill=(60, 60, 60))
    # 机（整頓されている） → desk_tidiness適合
    d.rectangle([60, 100, 360, 240], fill=(230, 220, 200), outline=(150, 140, 120), width=3)
    d.text((150, 155), "机（整頓済み）", font=f(20), fill=(90, 80, 60))
    # 書類2段 → stacking適合
    d.rectangle([620, 600, 740, 660], fill=(240, 240, 250), outline=(150, 150, 170), width=2)
    d.text((630, 615), "書類（2段積み）", font=f(16), fill=(80, 80, 100))
    img.save(path)
    print(f"saved {path}  GT違反: aisle_clear, fire_equipment_access, cable_management")


def scene_clean(path):
    """GT: 全ルール適合"""
    img = Image.new("RGB", (1000, 700), (245, 245, 240))
    d = ImageDraw.Draw(img)
    d.text((20, 15), "オフィス平面図（俯瞰）", font=f(26), fill=(30, 30, 30))
    d.rectangle([420, 60, 580, 680], outline=(150, 150, 150), width=3)
    d.text((445, 65), "通路（動線・障害物なし）", font=f(18), fill=(100, 100, 100))
    d.rectangle([880, 100, 960, 180], fill=(220, 60, 60))
    d.text((885, 125), "消火器", font=f(20), fill=(255, 255, 255))
    d.text((830, 195), "※前方に空間確保", font=f(16), fill=(60, 120, 60))
    d.rectangle([60, 100, 360, 240], fill=(230, 220, 200), outline=(150, 140, 120), width=3)
    d.text((150, 155), "机（整頓済み）", font=f(20), fill=(90, 80, 60))
    d.line([(60, 660), (400, 660)], fill=(90, 90, 90), width=8)
    d.text((100, 620), "ケーブル（壁沿い・カバー付き）", font=f(16), fill=(60, 60, 60))
    img.save(path)
    print(f"saved {path}  GT違反: なし")


if __name__ == "__main__":
    from pathlib import Path

    here = Path(__file__).parent
    scene_violations(here / "office_violations.png")
    scene_clean(here / "office_clean.png")

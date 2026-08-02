"""追加ドメイン（厨房・建設・クリアデスク）のGT既知テストシーン生成。

make_test_scene.py と同じ方式: 違反状態を意図的に配置した模式図を描画し、
どのルールに違反しているかを構成上既知にする。
"""
from PIL import Image, ImageDraw, ImageFont

FONT = "/Volumes/GM71TB/model-foundry/invoice-gen/fonts/NotoSansJP.ttf"


def f(sz):
    return ImageFont.truetype(FONT, sz)


def kitchen_violations(path):
    """GT違反: raw_cooked_separation, floor_dry, waste_bin_lid / 適合: fridge_temperature, soap_at_sink"""
    img = Image.new("RGB", (1000, 700), (248, 246, 240))
    d = ImageDraw.Draw(img)
    d.text((20, 15), "厨房 模式図（俯瞰）", font=f(26), fill=(30, 30, 30))
    # 調理台: 生肉トレイと調理済み料理が隣接 → raw_cooked_separation違反
    d.rectangle([60, 80, 480, 220], fill=(225, 225, 230), outline=(150, 150, 150), width=3)
    d.text((70, 88), "調理台", font=f(18), fill=(90, 90, 90))
    d.rectangle([90, 130, 230, 200], fill=(235, 150, 150), outline=(180, 80, 80), width=3)
    d.text((100, 155), "生肉トレイ", font=f(18), fill=(120, 30, 30))
    d.rectangle([240, 130, 400, 200], fill=(250, 230, 180), outline=(190, 160, 100), width=3)
    d.text((250, 155), "調理済み料理", font=f(18), fill=(120, 90, 30))
    d.text((90, 228), "※生肉と調理済みが隣どうしに置かれている", font=f(16), fill=(150, 60, 60))
    # 床の水たまり → floor_dry違反
    d.ellipse([560, 480, 780, 580], fill=(180, 210, 240), outline=(120, 160, 200), width=3)
    d.text((600, 520), "床の水たまり", font=f(18), fill=(50, 90, 140))
    # 蓋が開いたゴミ箱 → waste_bin_lid違反
    d.rectangle([870, 520, 960, 650], fill=(150, 150, 150), outline=(100, 100, 100), width=3)
    d.text((880, 570), "ゴミ箱", font=f(18), fill=(255, 255, 255))
    d.text((790, 660), "※蓋が開いたまま", font=f(16), fill=(150, 60, 60))
    # 冷蔵庫（温度計4℃） → fridge_temperature適合
    d.rectangle([60, 380, 220, 650], fill=(220, 230, 240), outline=(140, 160, 180), width=3)
    d.text((85, 420), "冷蔵庫", font=f(20), fill=(70, 90, 110))
    d.rectangle([90, 470, 190, 510], fill=(255, 255, 255), outline=(100, 100, 100), width=2)
    d.text((100, 478), "温度計 4℃", font=f(16), fill=(30, 90, 30))
    # 手洗いシンク（石けんあり） → soap_at_sink適合
    d.rectangle([560, 80, 940, 200], fill=(230, 238, 243), outline=(150, 160, 170), width=3)
    d.text((580, 95), "手洗いシンク", font=f(18), fill=(80, 90, 100))
    d.ellipse([850, 110, 900, 160], fill=(180, 230, 180), outline=(100, 160, 100), width=2)
    d.text((840, 168), "石けん", font=f(15), fill=(60, 110, 60))
    img.save(path)
    print(f"saved {path}  GT違反: raw_cooked_separation, floor_dry, waste_bin_lid")


def kitchen_clean(path):
    """GT: 全ルール適合"""
    img = Image.new("RGB", (1000, 700), (248, 246, 240))
    d = ImageDraw.Draw(img)
    d.text((20, 15), "厨房 模式図（俯瞰）", font=f(26), fill=(30, 30, 30))
    d.rectangle([60, 80, 480, 220], fill=(225, 225, 230), outline=(150, 150, 150), width=3)
    d.text((70, 88), "調理台（生食材ゾーン）", font=f(18), fill=(90, 90, 90))
    d.rectangle([90, 130, 230, 200], fill=(235, 150, 150), outline=(180, 80, 80), width=3)
    d.text((100, 155), "生肉トレイ", font=f(18), fill=(120, 30, 30))
    d.rectangle([560, 80, 940, 220], fill=(225, 225, 230), outline=(150, 150, 150), width=3)
    d.text((570, 88), "盛付台（調理済みゾーン・別の台）", font=f(18), fill=(90, 90, 90))
    d.rectangle([600, 130, 760, 200], fill=(250, 230, 180), outline=(190, 160, 100), width=3)
    d.text((610, 155), "調理済み料理", font=f(18), fill=(120, 90, 30))
    d.text((60, 300), "床: 乾燥・清掃済み", font=f(18), fill=(60, 110, 60))
    d.rectangle([870, 520, 960, 650], fill=(150, 150, 150), outline=(100, 100, 100), width=3)
    d.text((880, 570), "ゴミ箱", font=f(18), fill=(255, 255, 255))
    d.text((790, 660), "※蓋は閉じている", font=f(16), fill=(60, 110, 60))
    d.rectangle([60, 380, 220, 650], fill=(220, 230, 240), outline=(140, 160, 180), width=3)
    d.text((85, 420), "冷蔵庫", font=f(20), fill=(70, 90, 110))
    d.rectangle([90, 470, 190, 510], fill=(255, 255, 255), outline=(100, 100, 100), width=2)
    d.text((100, 478), "温度計 4℃", font=f(16), fill=(30, 90, 30))
    d.rectangle([400, 520, 700, 650], fill=(230, 238, 243), outline=(150, 160, 170), width=3)
    d.text((420, 535), "手洗いシンク", font=f(18), fill=(80, 90, 100))
    d.ellipse([610, 560, 660, 610], fill=(180, 230, 180), outline=(100, 160, 100), width=2)
    d.text((600, 618), "石けん", font=f(15), fill=(60, 110, 60))
    img.save(path)
    print(f"saved {path}  GT違反: なし")


def construction_violations(path):
    """GT違反: helmet_required, vest_required, opening_guard, material_storage / 適合: fire_watch, cord_protection"""
    img = Image.new("RGB", (1000, 700), (243, 242, 235))
    d = ImageDraw.Draw(img)
    d.text((20, 15), "建設現場 模式図（俯瞰）", font=f(26), fill=(30, 30, 30))
    # 作業者2名: 1名ヘルメットなし → helmet_required違反
    d.ellipse([150, 120, 210, 180], fill=(250, 210, 160), outline=(120, 90, 60), width=3)
    d.text((120, 190), "作業者A（ヘルメットなし）", font=f(16), fill=(150, 60, 60))
    d.ellipse([320, 120, 380, 180], fill=(240, 200, 60), outline=(160, 130, 30), width=4)
    d.text((300, 190), "作業者B（ヘルメット着用）", font=f(16), fill=(60, 110, 60))
    # 柵のない床開口部 → opening_guard違反
    d.rectangle([600, 120, 800, 260], fill=(60, 60, 70), outline=(200, 60, 60), width=4)
    d.text((640, 175), "床開口部", font=f(20), fill=(240, 240, 240))
    d.text((600, 270), "※柵・養生蓋なし", font=f(16), fill=(150, 60, 60))
    # 高さ2mの資材の山 → material_storage違反（基準1.5m）
    d.rectangle([80, 420, 320, 640], fill=(200, 180, 140), outline=(140, 120, 80), width=3)
    d.text((110, 480), "鋼材の山", font=f(20), fill=(90, 70, 40))
    d.text((110, 520), "高さ 2.0m", font=f(18), fill=(120, 40, 40))
    # 溶接エリア+隣に消火器 → fire_watch適合
    d.rectangle([600, 420, 800, 580], fill=(240, 220, 200), outline=(180, 140, 100), width=3)
    d.text((630, 450), "溶接作業エリア", font=f(18), fill=(120, 80, 40))
    d.rectangle([820, 480, 880, 580], fill=(220, 60, 60))
    d.text((825, 520), "消火器", font=f(16), fill=(255, 255, 255))
    # カバー付き仮設配線 → cord_protection適合
    d.line([(400, 660), (950, 660)], fill=(90, 90, 90), width=10)
    d.text((500, 620), "仮設配線（保護カバー付き）", font=f(16), fill=(70, 70, 70))
    img.save(path)
    print(f"saved {path}  GT違反: helmet_required, vest_required, opening_guard, material_storage")


def construction_clean(path):
    """GT: 全ルール適合（安全ベストも着用）"""
    img = Image.new("RGB", (1000, 700), (243, 242, 235))
    d = ImageDraw.Draw(img)
    d.text((20, 15), "建設現場 模式図（俯瞰）", font=f(26), fill=(30, 30, 30))
    # 訓練データ（gen_schematic.py draw_worker）と同一ジオメトリの人型
    for wx, name in [(170, "A"), (340, "B")]:
        y = 130
        d.ellipse([wx, y, wx + 28, y + 28], fill=(230, 200, 170),
                  outline=(120, 90, 60), width=2)
        d.pieslice([wx - 3, y - 8, wx + 31, y + 22], 180, 360,
                   fill=(240, 200, 60), outline=(160, 130, 30), width=2)
        d.rectangle([wx + 2, y + 30, wx + 26, y + 78], fill=(255, 140, 40),
                    outline=(70, 80, 100), width=2)
        d.line([wx + 8, y + 34, wx + 8, y + 74], fill=(230, 230, 90), width=3)
        d.line([wx + 20, y + 34, wx + 20, y + 74], fill=(230, 230, 90), width=3)
        d.text((wx - 55, y + 84), f"作業者{name}（ヘルメット着用・ベスト着用）",
               font=f(16), fill=(60, 110, 60))
    d.rectangle([600, 120, 800, 260], fill=(60, 60, 70), outline=(200, 60, 60), width=4)
    d.text((640, 175), "床開口部", font=f(20), fill=(240, 240, 240))
    d.rectangle([580, 100, 820, 280], outline=(230, 180, 60), width=6)
    d.text((590, 285), "※周囲に手すり柵を設置済み", font=f(16), fill=(60, 110, 60))
    d.rectangle([80, 480, 320, 640], fill=(200, 180, 140), outline=(140, 120, 80), width=3)
    d.text((110, 530), "鋼材（整理積み）", font=f(18), fill=(90, 70, 40))
    d.text((110, 570), "高さ 1.2m", font=f(18), fill=(60, 110, 60))
    d.rectangle([600, 420, 800, 580], fill=(240, 220, 200), outline=(180, 140, 100), width=3)
    d.text((630, 450), "溶接作業エリア", font=f(18), fill=(120, 80, 40))
    d.rectangle([820, 480, 880, 580], fill=(220, 60, 60))
    d.text((825, 520), "消火器", font=f(16), fill=(255, 255, 255))
    d.line([(400, 660), (950, 660)], fill=(90, 90, 90), width=10)
    d.text((500, 620), "仮設配線（保護カバー付き）", font=f(16), fill=(70, 70, 70))
    img.save(path)
    print(f"saved {path}  GT違反: なし")


def cleardesk_violations(path):
    """GT違反: no_unattended_documents, screen_lock, media_locked_storage / 適合: whiteboard_erased, cabinet_key"""
    img = Image.new("RGB", (1000, 700), (246, 246, 248))
    d = ImageDraw.Draw(img)
    d.text((20, 15), "執務室 模式図（俯瞰）・従業員は全員離席中", font=f(24), fill=(30, 30, 30))
    # 机: 書類の山 → no_unattended_documents違反
    d.rectangle([80, 100, 480, 300], fill=(230, 222, 205), outline=(150, 140, 120), width=3)
    d.text((100, 110), "机（離席中）", font=f(18), fill=(90, 80, 60))
    d.rectangle([140, 170, 300, 260], fill=(250, 250, 245), outline=(150, 150, 150), width=2)
    d.text((150, 200), "書類の山（放置）", font=f(16), fill=(120, 60, 60))
    # PC画面が表示されたまま → screen_lock違反
    d.rectangle([330, 150, 450, 240], fill=(120, 180, 240), outline=(60, 90, 130), width=3)
    d.text((340, 180), "PC画面", font=f(16), fill=(255, 255, 255))
    d.text((330, 248), "※資料が表示されたまま", font=f(14), fill=(150, 60, 60))
    # 机上のUSBメモリ → media_locked_storage違反
    d.rectangle([420, 265, 470, 290], fill=(90, 90, 100), outline=(50, 50, 60), width=2)
    d.text((350, 305), "USBメモリ（机上に放置）", font=f(15), fill=(150, 60, 60))
    # ホワイトボード（消去済み） → whiteboard_erased適合
    d.rectangle([600, 100, 940, 300], fill=(252, 252, 252), outline=(150, 150, 150), width=3)
    d.text((650, 130), "ホワイトボード", font=f(18), fill=(120, 120, 120))
    d.text((650, 200), "（記載なし・消去済み）", font=f(16), fill=(60, 110, 60))
    # キャビネット（施錠・鍵なし） → cabinet_key適合
    d.rectangle([80, 450, 320, 650], fill=(210, 210, 215), outline=(130, 130, 140), width=3)
    d.text((110, 500), "書類キャビネット", font=f(18), fill=(80, 80, 90))
    d.text((110, 540), "（施錠済み・鍵は挿さっていない）", font=f(14), fill=(60, 110, 60))
    img.save(path)
    print(f"saved {path}  GT違反: no_unattended_documents, screen_lock, media_locked_storage")


def cleardesk_clean(path):
    """GT: 全ルール適合"""
    img = Image.new("RGB", (1000, 700), (246, 246, 248))
    d = ImageDraw.Draw(img)
    d.text((20, 15), "執務室 模式図（俯瞰）・従業員は全員離席中", font=f(24), fill=(30, 30, 30))
    d.rectangle([80, 100, 480, 300], fill=(230, 222, 205), outline=(150, 140, 120), width=3)
    d.text((100, 110), "机（離席中・机上に何もない）", font=f(18), fill=(90, 80, 60))
    d.rectangle([330, 150, 450, 240], fill=(40, 40, 50), outline=(60, 90, 130), width=3)
    d.text((340, 180), "PC画面", font=f(16), fill=(180, 180, 190))
    d.text((330, 248), "※ロック中（黒画面）", font=f(14), fill=(60, 110, 60))
    d.rectangle([600, 100, 940, 300], fill=(252, 252, 252), outline=(150, 150, 150), width=3)
    d.text((650, 130), "ホワイトボード", font=f(18), fill=(120, 120, 120))
    d.text((650, 200), "（記載なし・消去済み）", font=f(16), fill=(60, 110, 60))
    d.rectangle([80, 450, 320, 650], fill=(210, 210, 215), outline=(130, 130, 140), width=3)
    d.text((110, 500), "書類キャビネット", font=f(18), fill=(80, 80, 90))
    d.text((110, 540), "（施錠済み・鍵は挿さっていない）", font=f(14), fill=(60, 110, 60))
    img.save(path)
    print(f"saved {path}  GT違反: なし")


if __name__ == "__main__":
    kitchen_violations("samples/kitchen_violations.png")
    kitchen_clean("samples/kitchen_clean.png")
    construction_violations("samples/construction_violations.png")
    construction_clean("samples/construction_clean.png")
    cleardesk_violations("samples/cleardesk_violations.png")
    cleardesk_clean("samples/cleardesk_clean.png")

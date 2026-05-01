#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BR_main.py – Binoküler Rekabet Deneyi (Binocular Rivalry Experiment)
=====================================================================
Afantazi araştırması için zihinsel imgeleme ve binoküler rekabet paradigması.
Katılımcılar kırmızı-camgöbeği (red-cyan) anaglif gözlük takarlar.

Deney Yapısı:
  - 1 baseline blok (sadece rekabet) + 8 imgeleme bloğu
  - Her blok: Kodlama (5s) → İmgeleme (25s) → Hazırlık (2s) → Rekabet (90s) → Dinlenme (30s)
  - Baseline blok kodlama ve imgeleme aşamalarını atlar.

Tuşlar:
  F = sol görsel baskın | J = sağ görsel baskın | BOŞLUK = karışık/geçiş
  ESC = deneyi güvenli şekilde sonlandır (veri kaydedilir)

Gereksinimler: PsychoPy (psychopy kütüphanesi)
"""

# =============================================================================
# Kütüphanelerin içe aktarılması
# =============================================================================
import os
import sys
import csv
import time
from datetime import datetime

from psychopy import visual, event, core, data, gui
from psychopy.hardware import keyboard

# =============================================================================
# Sabitler ve Yapılandırma
# =============================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STIM_ANAGLYPH_DIR = os.path.join(SCRIPT_DIR, "stimuli_anaglyph")
STIM_GRAY_DIR = os.path.join(SCRIPT_DIR, "stimuli_normalized")
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Görsel boyutları (8 derece görsel açı, 57cm mesafe, ~50px/derece = 400px)
STIM_SIZE_PX = (400, 400)
BG_COLOR = [0, 0, 0]  # PsychoPy normalized: 0 = RGB 128 (gri)

# Süre sabitleri (saniye)
DUR_ENCODING = 5
DUR_IMAGERY = 25
DUR_READY = 2
DUR_RIVALRY = 90
DUR_REST = 30
DUR_PRACTICE_RIVALRY = 30

# Uyaran çiftleri: (ev_no, yüz_kodu)
PAIRS = [
    (1, "F1"),  # Çift 1
    (2, "F2"),  # Çift 2
    (3, "M1"),  # Çift 3
    (4, "M2"),  # Çift 4
]

# Blok sırası: (blok_no, çift_indeksi, hayal_koşulu)
# çift_indeksi: 0-3 (PAIRS listesindeki indeks), hayal: "house"/"face"/"none"
BLOCK_ORDER = [
    (0, 0, "none"),      # Baseline
    (1, 0, "house"),     # Çift 1 – ev hayal et
    (2, 0, "face"),      # Çift 1 – yüz hayal et
    (3, 1, "face"),      # Çift 2 – yüz hayal et
    (4, 1, "house"),     # Çift 2 – ev hayal et
    (5, 2, "house"),     # Çift 3 – ev hayal et
    (6, 2, "face"),      # Çift 3 – yüz hayal et
    (7, 3, "face"),      # Çift 4 – yüz hayal et
    (8, 3, "house"),     # Çift 4 – ev hayal et
]


# =============================================================================
# Yardımcı Fonksiyonlar
# =============================================================================
def get_stim_paths(pair_idx):
    """Verilen çift için anaglif uyaran dosya yollarını döndürür."""
    house_num, face_code = PAIRS[pair_idx]
    return {
        "house_RED":  os.path.join(STIM_ANAGLYPH_DIR, f"house_{house_num}_RED.png"),
        "house_CYAN": os.path.join(STIM_ANAGLYPH_DIR, f"house_{house_num}_CYAN.png"),
        "face_RED":   os.path.join(STIM_ANAGLYPH_DIR, f"face_{face_code}_RED.png"),
        "face_CYAN":  os.path.join(STIM_ANAGLYPH_DIR, f"face_{face_code}_CYAN.png"),
    }


def get_gray_path(pair_idx, category):
    """Kodlama aşaması için gri tonlama görselinin yolunu döndürür."""
    house_num, face_code = PAIRS[pair_idx]
    if category == "house":
        return os.path.join(STIM_GRAY_DIR, f"house_{house_num}_norm.png")
    else:
        return os.path.join(STIM_GRAY_DIR, f"face_{face_code}_norm.png")


def show_text_and_wait(win, message, duration=None, keys=None):
    """Ekranda metin gösterir; süre veya tuş beklenir."""
    txt = visual.TextStim(win, text=message, color="white", height=28,
                          wrapWidth=800, font="Arial")
    txt.draw()
    win.flip()
    if duration:
        core.wait(duration, hogCPUperiod=0.2)
    elif keys:
        event.waitKeys(keyList=keys)


def safe_quit(win, data_rows, filepath):
    """ESC ile güvenli çıkış: veriyi kaydeder ve kapatır."""
    save_data(data_rows, filepath)
    win.close()
    core.quit()


def save_data(data_rows, filepath):
    """Veriyi CSV dosyasına kaydeder."""
    if not data_rows:
        return
    fieldnames = [
        "participant_id", "block_number", "block_type", "pair_number",
        "imagine_condition", "house_eye", "face_eye",
        "percept_onset", "percept_offset", "percept_duration",
        "key_pressed", "dominant_stimulus", "trial_time"
    ]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data_rows)
    print(f"Veri kaydedildi: {filepath}")


def determine_dominant(key, house_eye):
    """Basılan tuşa göre baskın uyaranı belirler."""
    if key == "space":
        return "mixed"
    if key == "f":  # sol görsel baskın
        return "house" if house_eye == "left" else "face"
    if key == "j":  # sağ görsel baskın
        return "house" if house_eye == "right" else "face"
    return "unknown"


# =============================================================================
# Rekabet (Rivalry) Fazı
# =============================================================================
def run_rivalry_phase(win, pair_idx, house_eye, duration, participant_id,
                      block_number, block_type, pair_number, imagine_condition,
                      data_rows, filepath):
    """
    Anaglif uyaranları gösterir ve katılımcı yanıtlarını kaydeder.
    F = sol baskın, J = sağ baskın, BOŞLUK = karışık
    """
    face_eye = "right" if house_eye == "left" else "left"
    paths = get_stim_paths(pair_idx)

    # Göz atamasına göre uyaranları belirle
    if house_eye == "left":
        # Ev kırmızı (sol göz), Yüz camgöbeği (sağ göz)
        stim_red_path = paths["house_RED"]
        stim_cyan_path = paths["face_CYAN"]
    else:
        # Yüz kırmızı (sol göz), Ev camgöbeği (sağ göz)
        stim_red_path = paths["face_RED"]
        stim_cyan_path = paths["house_CYAN"]

    # Uyaran nesnelerini oluştur (üst üste bindirilecek)
    stim_red = visual.ImageStim(win, image=stim_red_path, size=STIM_SIZE_PX,
                                pos=(0, 0), units="pix")
    stim_cyan = visual.ImageStim(win, image=stim_cyan_path, size=STIM_SIZE_PX,
                                 pos=(0, 0), units="pix")

    # İlerleme çubuğu arka planı
    bar_bg = visual.Rect(win, width=600, height=16, pos=(0, -340),
                         fillColor="gray", lineColor="gray", units="pix")
    bar_fill = visual.Rect(win, width=0, height=16, pos=(0, -340),
                           fillColor="white", lineColor="white", units="pix")

    # Etiketler
    label_f = visual.TextStim(win, text="F = Sol", pos=(-250, -370),
                              color="white", height=18, units="pix")
    label_j = visual.TextStim(win, text="J = Sağ", pos=(250, -370),
                              color="white", height=18, units="pix")
    label_sp = visual.TextStim(win, text="BOŞLUK = Karışık", pos=(0, -395),
                               color="white", height=18, units="pix")

    # Zamanlayıcı ve yanıt değişkenleri
    rivalry_clock = core.Clock()
    current_key = None
    current_onset = None

    # Yeni PsychoPy keyboard API — daha güvenilir tuş algılama
    kb = keyboard.Keyboard(clock=rivalry_clock)
    kb.clearEvents()

    rivalry_clock.reset()
    while rivalry_clock.getTime() < duration:
        elapsed = rivalry_clock.getTime()
        progress = elapsed / duration

        # İlerleme çubuğu güncelle
        fill_w = 600 * progress
        bar_fill.width = fill_w
        bar_fill.pos = (-300 + fill_w / 2, -340)

        # Çizim — additive blending ile anaglif birleştirme
        # (kırmızı + cyan kanallar toplanarak tek piksel oluşturur)
        win.blendMode = 'add'
        stim_red.draw()
        stim_cyan.draw()
        win.blendMode = 'avg'
        bar_bg.draw()
        bar_fill.draw()
        label_f.draw()
        label_j.draw()
        label_sp.draw()
        win.flip()

        # Tuş kontrolü — rivalry_clock ile senkronize zaman damgası
        now = rivalry_clock.getTime()
        pressed = kb.getKeys(keyList=["f", "j", "space", "escape"], clear=True)

        for key_obj in pressed:
            key = key_obj.name
            # Güvenilir zaman: key_obj.rt yerine şimdiki clock zamanı kullan
            # (rt değerleri bazen monoton olmayabiliyor)
            t_stamp = max(now, current_onset if current_onset is not None else 0)

            # ESC kontrolü
            if key == "escape":
                if current_key is not None:
                    data_rows.append({
                        "participant_id": participant_id,
                        "block_number": block_number,
                        "block_type": block_type,
                        "pair_number": pair_number,
                        "imagine_condition": imagine_condition,
                        "house_eye": house_eye,
                        "face_eye": face_eye,
                        "percept_onset": round(current_onset, 4),
                        "percept_offset": round(t_stamp, 4),
                        "percept_duration": round(max(0, t_stamp - current_onset), 4),
                        "key_pressed": current_key.upper() if current_key != "space" else "SPACE",
                        "dominant_stimulus": determine_dominant(current_key, house_eye),
                        "trial_time": datetime.now().isoformat()
                    })
                safe_quit(win, data_rows, filepath)

            # Yeni tuş basıldığında önceki algıyı kaydet
            if key != current_key:
                if current_key is not None:
                    data_rows.append({
                        "participant_id": participant_id,
                        "block_number": block_number,
                        "block_type": block_type,
                        "pair_number": pair_number,
                        "imagine_condition": imagine_condition,
                        "house_eye": house_eye,
                        "face_eye": face_eye,
                        "percept_onset": round(current_onset, 4),
                        "percept_offset": round(t_stamp, 4),
                        "percept_duration": round(max(0, t_stamp - current_onset), 4),
                        "key_pressed": current_key.upper() if current_key != "space" else "SPACE",
                        "dominant_stimulus": determine_dominant(current_key, house_eye),
                        "trial_time": datetime.now().isoformat()
                    })
                current_key = key
                current_onset = now  # rivalry_clock'un şimdiki değerini kullan

    # Son algıyı kaydet
    if current_key is not None:
        offset = duration
        data_rows.append({
            "participant_id": participant_id,
            "block_number": block_number,
            "block_type": block_type,
            "pair_number": pair_number,
            "imagine_condition": imagine_condition,
            "house_eye": house_eye,
            "face_eye": face_eye,
            "percept_onset": round(current_onset, 4),
            "percept_offset": round(offset, 4),
            "percept_duration": round(offset - current_onset, 4),
            "key_pressed": current_key.upper() if current_key != "space" else "SPACE",
            "dominant_stimulus": determine_dominant(current_key, house_eye),
            "trial_time": datetime.now().isoformat()
        })


# =============================================================================
# Faz Fonksiyonları
# =============================================================================
def run_encoding_phase(win, pair_idx, imagine_condition):
    """Faz 1 – Kodlama: Hedef görseli 5 saniye gösterir."""
    gray_path = get_gray_path(pair_idx, imagine_condition)
    stim = visual.ImageStim(win, image=gray_path, size=STIM_SIZE_PX,
                            pos=(0, 40), units="pix")
    instruction = visual.TextStim(win, text="Bu görseli dikkatlice inceleyin",
                                  pos=(0, -250), color="white", height=24,
                                  units="pix", font="Arial")
    stim.draw()
    instruction.draw()
    win.flip()

    # 5 saniye bekle, ESC kontrolü ile
    timer = core.Clock()
    while timer.getTime() < DUR_ENCODING:
        if "escape" in event.getKeys(keyList=["escape"]):
            return False
        core.wait(0.05)
    return True


def run_imagery_phase(win):
    """Faz 2 – İmgeleme: Siyah ekran, fiksasyon çarpısı ve geri sayım (25s)."""
    fix_cross = visual.TextStim(win, text="+", color="white", height=48,
                                pos=(0, 60), units="pix", font="Arial")
    instruction = visual.TextStim(win,
                                  text="Gözlerinizi açık tutarak bu görseli\nzihninizde canlandırın",
                                  pos=(0, -80), color="white", height=22,
                                  wrapWidth=700, units="pix", font="Arial")
    countdown = visual.TextStim(win, text="", pos=(0, -160), color="yellow",
                                height=36, units="pix", font="Arial")

    timer = core.Clock()
    while timer.getTime() < DUR_IMAGERY:
        remaining = int(DUR_IMAGERY - timer.getTime()) + 1
        if remaining > DUR_IMAGERY:
            remaining = DUR_IMAGERY

        win.color = [-1, -1, -1]  # Siyah arka plan
        fix_cross.draw()
        instruction.draw()
        countdown.text = str(remaining)
        countdown.draw()
        win.flip()

        if "escape" in event.getKeys(keyList=["escape"]):
            win.color = BG_COLOR
            return False
        core.wait(0.05)

    win.color = BG_COLOR
    return True


def run_ready_phase(win):
    """Faz 3 – Hazırlık: 2 saniye hazırlanma mesajı."""
    show_text_and_wait(win, "Hazır olun...\nGözlüğünüzü takın", duration=DUR_READY)


def run_rest_phase(win):
    """Faz 5 – Dinlenme: 30 saniye karanlık ekran."""
    win.color = [-1, -1, -1]
    txt = visual.TextStim(win,
                          text="Dinlenin.\nGözlerinizi bir süre kapatabilirsiniz.",
                          color="white", height=24, wrapWidth=700,
                          units="pix", font="Arial")
    timer = core.Clock()
    while timer.getTime() < DUR_REST:
        txt.draw()
        win.flip()
        if "escape" in event.getKeys(keyList=["escape"]):
            win.color = BG_COLOR
            return False
        core.wait(0.1)
    win.color = BG_COLOR
    return True


# =============================================================================
# Ana Deney Fonksiyonu
# =============================================================================
def main():
    # -------------------------------------------------------------------------
    # Katılımcı bilgi diyalogu
    # -------------------------------------------------------------------------
    dlg = gui.Dlg(title="Binoküler Rekabet Deneyi")
    dlg.addField("Katılımcı ID:", "001")
    dlg.addField("Yaş:", "")
    dlg.addField("Cinsiyet:", choices=["Kadın", "Erkek", "Diğer"])
    dlg_data = dlg.show()
    if not dlg.OK:
        core.quit()

    participant_id = dlg_data[0]
    participant_age = dlg_data[1]
    participant_gender = dlg_data[2]

    # Veri dosyası yolu
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"BR_{participant_id}_{date_str}.csv"
    csv_filepath = os.path.join(DATA_DIR, csv_filename)

    # Veri satırları listesi
    data_rows = []

    # -------------------------------------------------------------------------
    # Göz-renk ataması (tek/çift katılımcı numarasına göre)
    # -------------------------------------------------------------------------
    try:
        pid_num = int(participant_id)
    except ValueError:
        pid_num = sum(ord(c) for c in participant_id)

    if pid_num % 2 == 1:  # Tek numara
        house_eye = "left"   # Ev = RED (sol göz)
        face_eye = "right"   # Yüz = CYAN (sağ göz)
    else:                    # Çift numara
        house_eye = "right"  # Ev = CYAN (sağ göz)
        face_eye = "left"    # Yüz = RED (sol göz)

    print(f"Katılımcı {participant_id}: ev={house_eye} göz, yüz={face_eye} göz")

    # -------------------------------------------------------------------------
    # Pencere oluşturma
    # -------------------------------------------------------------------------
    win = visual.Window(fullscr=True, color=BG_COLOR, units="pix",
                        monitor="testMonitor", allowGUI=False)
    win.mouseVisible = False
    event.globalKeys.clear()

    # -------------------------------------------------------------------------
    # Yönerge ekranı
    # -------------------------------------------------------------------------
    instructions = (
        "Bu çalışmada anaglif gözlük takarak iki farklı görsel arasındaki\n"
        "algısal rekabeti inceleyeceğiz.\n\n"
        "F tuşu = sol görsel baskın\n"
        "J tuşu = sağ görsel baskın\n"
        "BOŞLUK = karışık / geçiş\n\n"
        "Tuşu basılı tutun, algınız değişince bırakıp yenisine basın.\n\n"
        "Devam etmek için herhangi bir tuşa basın."
    )
    show_text_and_wait(win, instructions, keys=["space", "return"])

    # -------------------------------------------------------------------------
    # Alıştırma denemesi (30 saniye rekabet, imgeleme yok)
    # -------------------------------------------------------------------------
    show_text_and_wait(win,
                       "Şimdi kısa bir alıştırma yapacaksınız.\n"
                       "Gözlüğünüzü takın.\n\n"
                       "Devam etmek için herhangi bir tuşa basın.",
                       keys=["space", "return"])

    # Alıştırma için ilk çifti kullan (veri kaydedilmez)
    practice_rows = []
    run_rivalry_phase(win, pair_idx=0, house_eye=house_eye,
                      duration=DUR_PRACTICE_RIVALRY,
                      participant_id=participant_id,
                      block_number=-1, block_type="practice",
                      pair_number=0, imagine_condition="none",
                      data_rows=practice_rows, filepath=csv_filepath)

    show_text_and_wait(win,
                       "Alıştırma tamamlandı.\n\n"
                       "Asıl deneye başlamak için herhangi bir tuşa basın.",
                       keys=["space", "return"])

    # -------------------------------------------------------------------------
    # Ana deney döngüsü
    # -------------------------------------------------------------------------
    for block_num, pair_idx, imagine_cond in BLOCK_ORDER:
        pair_number = pair_idx + 1

        # Blok türünü belirle
        if imagine_cond == "none":
            block_type = "baseline"
        elif imagine_cond == "house":
            block_type = "house_imagery"
        else:
            block_type = "face_imagery"

        # --- BASELINE BLOĞU ---
        if block_type == "baseline":
            show_text_and_wait(win,
                               f"Blok {block_num + 1} / {len(BLOCK_ORDER)}\n\n"
                               "Sadece gördüklerinizi bildirin.\n"
                               "Herhangi bir şey hayal etmeye çalışmayın.\n\n"
                               "Gözlüğünüzü takın.\n"
                               "Devam etmek için herhangi bir tuşa basın.",
                               keys=["space", "return"])

            run_rivalry_phase(win, pair_idx=pair_idx, house_eye=house_eye,
                              duration=DUR_RIVALRY,
                              participant_id=participant_id,
                              block_number=block_num,
                              block_type=block_type,
                              pair_number=pair_number,
                              imagine_condition=imagine_cond,
                              data_rows=data_rows, filepath=csv_filepath)

        # --- İMGELEME BLOKLARI ---
        else:
            # Blok başlangıç ekranı
            cond_text = "EV" if imagine_cond == "house" else "YÜZ"
            show_text_and_wait(win,
                               f"Blok {block_num + 1} / {len(BLOCK_ORDER)}\n\n"
                               f"Bu blokta bir {cond_text} görseli hayal edeceksiniz.\n\n"
                               "Devam etmek için herhangi bir tuşa basın.",
                               keys=["space", "return"])

            # Faz 1: Kodlama
            ok = run_encoding_phase(win, pair_idx, imagine_cond)
            if not ok:
                safe_quit(win, data_rows, csv_filepath)

            # Faz 2: İmgeleme indüksiyonu
            ok = run_imagery_phase(win)
            if not ok:
                safe_quit(win, data_rows, csv_filepath)

            # Faz 3: Hazırlık
            run_ready_phase(win)

            # Faz 4: Rekabet
            run_rivalry_phase(win, pair_idx=pair_idx, house_eye=house_eye,
                              duration=DUR_RIVALRY,
                              participant_id=participant_id,
                              block_number=block_num,
                              block_type=block_type,
                              pair_number=pair_number,
                              imagine_condition=imagine_cond,
                              data_rows=data_rows, filepath=csv_filepath)

        # Faz 5: Dinlenme (son bloktan sonra hariç)
        if block_num < BLOCK_ORDER[-1][0]:
            ok = run_rest_phase(win)
            if not ok:
                safe_quit(win, data_rows, csv_filepath)

        # Her blok sonunda ara kayıt (güvenlik)
        save_data(data_rows, csv_filepath)

    # -------------------------------------------------------------------------
    # Deney sonu
    # -------------------------------------------------------------------------
    show_text_and_wait(win,
                       "Teşekkürler!\nÇalışma tamamlandı.\n\n"
                       "Çıkmak için herhangi bir tuşa basın.",
                       keys=["space", "return", "escape"])

    save_data(data_rows, csv_filepath)
    win.close()
    core.quit()


# =============================================================================
# Çalıştırma
# =============================================================================
if __name__ == "__main__":
    main()

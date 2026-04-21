# 🎓 Davlat Tili va Umumiy Bilimlar — Telegram Test Boti

## 📋 Xususiyatlari
- **121 ta savol** (Davlat tili, tarix, adabiyot, ish yuritish, pedagogika va boshqalar)
- Har bir test sessiyasida **50 ta tasodifiy savol**
- **1 soat** vaqt chegarasi (60 daqiqa)
- 10 daqiqa qolganda **avtomatik ogohlantirish**
- Test oxirida **baho va foiz** ko'rsatiladi
- Inline tugmachalar bilan qulay interfeys

## ⚙️ O'rnatish

### 1. Kerakli kutubxonalarni o'rnatish
```bash
pip install -r requirements.txt
```

### 2. Bot tokenini sozlash
`config.py` faylini oching va `YOUR_BOT_TOKEN_HERE` o'rniga o'z tokeningizni kiriting:
```python
BOT_TOKEN = "1234567890:ABCDefGhIJKlmNoPQRsTUVwxyZ"
```

Token olish uchun: [@BotFather](https://t.me/BotFather) → `/newbot`

### 3. Botni ishga tushirish
```bash
python bot.py
```

## 📱 Bot buyruqlari
| Buyruq | Tavsif |
|--------|--------|
| `/start` | Botni ishga tushirish |
| `/test` | Yangi test boshlash |
| `/status` | Joriy test holati |
| `/stop` | Testni to'xtatish |
| `/help` | Yordam |

## 🏆 Baho tizimi
| Foiz | Baho |
|------|------|
| 86–100% | ⭐⭐⭐⭐⭐ A'lo (5) |
| 71–85% | ⭐⭐⭐⭐ Yaxshi (4) |
| 56–70% | ⭐⭐⭐ Qoniqarli (3) |
| 0–55% | ⭐ Qoniqarsiz (2) |

## 📂 Fayl tuzilmasi
```
davlat_tili_bot/
├── bot.py           — Asosiy bot kodi
├── questions.py     — 121 ta savol bazasi
├── config.py        — Token va sozlamalar
├── requirements.txt — Kerakli kutubxonalar
└── README.md        — Ushbu fayl
```

## ➕ Yangi savollar qo'shish
`questions.py` fayliga quyidagi formatda qo'shing:
```python
{
    "id": 122,
    "question": "Savol matni?",
    "options": [
        "Variant A",
        "Variant B",
        "Variant C",
        "Variant D"
    ],
    "correct": 0,  # 0=A, 1=B, 2=C, 3=D
    "category": "Kategoriya nomi"
},
```

## 🖥 Server (doim ishlash uchun)
```bash
# nohup bilan
nohup python bot.py &

# screen bilan
screen -S testbot
python bot.py
# Ctrl+A, D — fon rejimiga o'tish
```

## 📌 Talablar
- Python 3.8 yoki undan yuqori
- Internetga ulanish
- Telegram Bot Token (BotFather orqali)

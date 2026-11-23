# Data Cleaner

تطبيق ويب (Flask) بيرفع ملف Excel أو CSV ويرجعلك ملف Excel نضيف.

## بيعمل إيه
- يشيل الصفوف المكررة
- يمسح الصفوف الفاضية بالكامل
- يشيل المسافات الزيادة من الخانات النصية
- يوحّد شكل أسماء الأعمدة (Title Case)
- لو الملف Excel فيه أكتر من شيت، بينضّف كل الشيتات
- ملفات CSV العربي (UTF-8 أو Windows-1256) والفاصلة `,` أو `;` بتتقرأ صح

## التشغيل على Windows
دوس دبل كليك على `run.bat` — بيعمل البيئة ويسطّب المكتبات ويفتح المتصفح لوحده.

## التشغيل اليدوي
```bash
python -m venv venv
venv\Scripts\activate        # على Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
python app.py
```
بعدها افتح http://127.0.0.1:5000

## هيكل المشروع
```
data_cleaner/
├── app.py              # كود التطبيق
├── requirements.txt    # المكتبات المطلوبة
├── run.bat             # تشغيل سريع على Windows
├── README.md
├── templates/
│   └── index.html      # الصفحة الرئيسية
└── static/
    └── style.css       # التنسيق
```

الحد الأقصى لحجم الملف: 20 ميجا (تقدر تغيّره من `MAX_UPLOAD_MB` في `app.py`).

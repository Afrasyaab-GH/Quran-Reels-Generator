# 1. استخدام نسخة Bullseye المستقرة
FROM python:3.9-bullseye

WORKDIR /app

# 2. تثبيت البرامج الضرورية
# استبدلنا fonts-noto بـ fonts-kacst (خطوط عربية خفيفة ومضمونة)
RUN apt-get update && \
    apt-get install -y \
    git \
    ffmpeg \
    imagemagick \
    ghostscript \
    fonts-liberation \
    fonts-kacst && \
    rm -rf /var/lib/apt/lists/*

# 3. فتح قيود ImageMagick بالكامل (الحل النووي)
# ده بيسمح بقراءة الملفات المؤقتة (@) والنصوص (TXT)
RUN echo '<policymap> \
    <policy domain="path" rights="read|write" pattern="@*" /> \
    <policy domain="coder" rights="read|write" pattern="TXT" /> \
    <policy domain="coder" rights="read|write" pattern="LABEL" /> \
</policymap>' > /etc/ImageMagick-6/policy.xml

# 4. إنشاء المستخدم
RUN useradd -m -u 1000 user

# 5. سحب الكود (أول خطوة في التعامل مع الملفات عشان الفولدر يكون فاضي)
RUN git clone https://github.com/AliMahmoudDev/Quran-Reels-Generator.git .

# 6. تثبيت المكتبات
RUN pip install --no-cache-dir -r requirements.txt

# 7. إنشاء المجلدات وإعطاء صلاحيات كاملة (777)
# عملنا فولدر my_temp عشان نبعد عن فولدرات النظام المحمية
# ✅ data folder للبيانات الدائمة (DB + outputs)
RUN mkdir -p /app/data /app/data/outputs /app/my_temp /app/temp_videos /app/vision /app/temp_audio && \
    chown -R user:user /app && \
    chmod -R 777 /app

# 8. توجيه الملفات المؤقتة للفولدر بتاعنا
ENV TMPDIR=/app/my_temp
ENV TEMP=/app/my_temp
ENV TMP=/app/my_temp
ENV IMAGEMAGICK_BINARY=/usr/bin/convert

# 9. التشغيل
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

ENV FLASK_APP=main.py
CMD ["flask", "run", "--host=0.0.0.0", "--port=7860"]
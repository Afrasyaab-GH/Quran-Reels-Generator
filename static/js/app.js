        // ═══════════════════════════════════════
        // 📦 State & Config
        // ═══════════════════════════════════════
        let VERSE_COUNTS = {};
        let currentJobId = null;
        let pollInterval = null;
        let SESSION_ID = null;
        let CURRENT_LANG = localStorage.getItem('quran_ui_lang') || 'ar';
        let currentResultJobId = null;
        let currentResultConfig = null;
        let mediaHubFilter = 'all';

        const I18N = {
            ar: {
                appTitle: 'صانع الريلز القرآني',
                appSubtitle: 'نسخة التوربو',
                tabMain: '🏠 الرئيسية',
                tabBatch: '📦 دفعة متعددة',
                tabHistory: '📜 السجل',
                tabSettings: '⚙️ إعدادات',
                reciter: '🎤 القارئ',
                surah: '📖 السورة',
                ayahRange: '📍 نطاق الآيات',
                fromAyah: 'من آية',
                toAyah: 'إلى آية',
                estimatedTimePrefix: '⏱️ الوقت التقريبي:',
                bgChangeAyah: 'تغيير الخلفية مع الآيات',
                bgChangeAyahHint: 'كل آية بخلفية مختلفة',
                textGlow: 'توهج النص',
                textGlowHint: 'تأثير هالة حول النص',
                cinematicDim: 'تعتيم سينمائي',
                cinematicDimHint: 'تأثير سينمائي خافت',
                advancedOptions: 'خيارات متقدمة',
                fpsLabel: 'سلاسة الفيديو (FPS)',
                qualityLabel: 'جودة الفيديو',
                aspectRatioLabel: '📐 أبعاد الفيديو',
                quranFontLabel: '✒️ خط المصحف',
                translationFontLabel: '🔤 خط الترجمة',
                customBgSearch: 'بحث خلفية مخصص',
                bgQueryPlaceholder: 'اكتب: بحر، سماء، جبال...',
                random: '🎲 عشوائي',
                generateVideoBtn: '✨ إنشاء الفيديو',
                stopBtn: '🛑 إيقاف',
                preparing: 'جاري التحضير...',
                remaining: '⏳ متبقي:',
                download: '⬇️ تحميل',
                newVideo: '🔄 فيديو جديد',
                batchHeader: '📦 إنشاء دفعة فيديوهات',
                batchSubheader: 'أضف فيديوهات للقائمة ثم ابدأ الإنشاء',
                randomReciters: '🎤 قراء العشوائي',
                selectAll: 'تحديد الكل',
                deselectAll: 'إلغاء الكل',
                addToList: '➕ إضافة للقائمة',
                batchListTitle: '📋 قائمة الفيديوهات',
                batchEmpty: 'لم تتم إضافة أي فيديوهات',
                totalEstimatedPrefix: '⏱️ الوقت الكلي التقريبي:',
                startBatchBtn: '🚀 إنشاء الدفعة',
                videosWord: 'فيديو',
                cancelBatchBtn: '🛑 إلغاء الدفعة',
                historyTitle: 'سجل الفيديوهات',
                clearAll: '🗑️ مسح الكل',
                noHistory: 'لا توجد فيديوهات في السجل',
                preview: '▶️ عرض',
                youtube: '📺 يوتيوب',
                unavailable: 'غير متاح',
                unspecified: 'غير محدد',
                arabicText: 'النص العربي',
                englishTranslation: 'الترجمة الإنجليزية',
                color: 'اللون',
                size: 'الحجم',
                outlineColor: 'لون الإطار',
                outlineWidth: 'سمك الإطار',
                pexelsKeyOptional: 'مفتاح Pexels (اختياري)',
                pexelsPlaceholder: 'اتركه فارغاً للاستخدام الافتراضي',
                saveSettingsBtn: '💾 حفظ الإعدادات',
                restoreDefaultsBtn: 'استعادة الافتراضي',
                processingRunning: 'جاري المعالجة... ({current}/{total})',
                completed: '✅ اكتمل!',
                cancelled: '⚠️ تم الإلغاء',
                waiting: '⏳ في الانتظار...',
                currentVideoPrefix: '🎬',
                remainingTimePrefix: '⏱️ الوقت المتبقي:',
                ayahWord: 'آية',
                secShort: 'ث',
                minShort: 'د',
                hourShort: 'س',
                secondWord: 'ثانية',
                minuteWord: 'دقيقة',
                hourWord: 'ساعة',
                maxAyahOnly: 'هذه السورة بها {max} آية فقط',
                loadingConfigFailed: 'فشل تحميل الإعدادات',
                generationStartFailed: 'فشل بدء المعالجة',
                networkError: 'حدث خطأ في الاتصال',
                processing: 'جاري المعالجة...',
                unknownError: 'حدث خطأ',
                videoCreated: 'تم إنشاء الفيديو بنجاح!',
                stopConfirm: 'هل تريد إيقاف المعالجة؟',
                stopDone: 'تم الإيقاف',
                loadingVideo: 'جاري تحميل الفيديو...',
                loadingVideoFailed: 'فشل تحميل الفيديو',
                deleteItemConfirm: 'حذف هذا العنصر؟',
                deleted: 'تم الحذف',
                deleteFailed: 'فشل الحذف',
                clearHistoryConfirm: 'مسح كل السجل؟ لا يمكن التراجع.',
                historyCleared: 'تم مسح السجل',
                historyClearFailed: 'فشل مسح السجل',
                settingsSaved: 'تم حفظ الإعدادات',
                resetSettingsConfirm: 'استعادة الإعدادات الافتراضية؟',
                settingsRestored: 'تم استعادة الإعدادات',
                calculating: '⏳ جاري الحساب...',
                maxBatchLimit: 'الحد الأقصى هو {max} فيديو في الدفعة الواحدة',
                alreadyInBatch: 'هذا الفيديو موجود بالفعل في القائمة',
                addedToBatch: 'تمت الإضافة: {surah} ({reciter})',
                addBatchFirst: 'أضف فيديوهات للقائمة أولاً',
                creatingBatch: 'جاري إنشاء الدفعة...',
                batchCreated: 'تم إنشاء دفعة من {count} فيديو',
                batchCreateFailed: 'فشل إنشاء الدفعة',
                batchCancelled: 'تم إلغاء الدفعة',
                batchCreatedDone: 'تم إنشاء {count} فيديو بنجاح!',
                youtubeNotConfigured: '⚠️ ميزة يوتيوب غير مُعدة. تواصل مع المطور.',
                youtubeAuthOpening: 'سيتم فتح نافذة المصادقة...',
                youtubeLinked: '✅ تم ربط يوتيوب بنجاح!',
                youtubeRedirectHint: '⚠️ قد تحتاج لإضافة الـ Redirect URI في Google Cloud Console',
                youtubeDialogTitle: '📺 نشر على يوتيوب',
                ytTitleLabel: '📌 العنوان',
                ytTitlePlaceholder: 'عنوان الفيديو',
                ytDescriptionLabel: '📝 الوصف',
                ytDescriptionPlaceholder: 'وصف الفيديو',
                ytTagsLabel: '🏷️ الكلمات المفتاحية (مفصولة بفاصلة)',
                ytTagsPlaceholder: 'قرآن, تلاوة, إسلام',
                ytPrivacyLabel: '🔒 الخصوصية',
                ytPrivacyUnlisted: '🔗 غير مدرج (للأصدقاء فقط)',
                ytPrivacyPrivate: '🔐 خاص',
                ytPrivacyPublic: '🌍 عام',
                ytPrivacyScheduled: '📅 مجدول (عام في وقت محدد)',
                ytScheduleLabel: '📆 وقت النشر المجدول',
                ytScheduleNote: '⚠️ يجب أن يكون الوقت على الأقل ساعة من الآن',
                ytPublishNow: '📤 نشر الآن',
                ytSchedulePublish: '📅 جدولة النشر',
                ytCancel: 'إلغاء',
                ytUploading: '⏳ جاري الرفع... يرجى الانتظار',
                schedulePickTime: '⚠️ الرجاء اختيار وقت للجدولة',
                scheduleMin15: '⚠️ يجب أن يكون وقت الجدولة بعد 15 دقيقة على الأقل',
                scheduledSuccess: '✅ تم جدولة الفيديو بنجاح!',
                publishedSuccess: '✅ تم نشر الفيديو بنجاح!',
                youtubeMustConnect: '⚠️ يجب ربط حساب يوتيوب أولاً',
                uploadFailed: 'فشل في الرفع',
                connectionFailed: '❌ فشل في الاتصال',
                runningJobResume: '🎬 فيديو قيد المعالجة!\n📊 التقدم: {percent}%\n\nهل تريد متابعته؟',
                scheduledConfirm: 'تم جدولة الفيديو!\n\nسيُنشر في: {time}\n\nهل تريد فتح الفيديو؟\n{url}',
                publishedConfirm: 'تم النشر بنجاح!\n\nهل تريد فتح الفيديو؟\n{url}',
                englishShort: 'EN',
                arabicShort: 'AR',
                bgEnhanceLabel: '✨ Background Enhancement',
                bgEnhanceHint: 'Improve background visual quality',
                bgEnhanceSmart: '🌟 Smart enhance (default)',
                bgEnhanceDark: '🌙 Dark background',
                bgEnhanceSaturate: '🎨 Rich colors',
                bgEnhanceNone: '⚪ No effect',
                bannerTitle: 'No Pexels API key',
                bannerTextBefore: '— Videos will use an animated gradient background instead of real videos. Get a free key from',
                bannerTextAfter: 'then paste it here:',
                bannerSave: 'Save',
                bannerDismiss: 'Hide'
            },
            en: {
                appTitle: 'Quran Reels Generator',
                appSubtitle: 'Turbo Edition',
                tabMain: '🏠 Home',
                tabBatch: '📦 Batch',
                tabHistory: '📜 History',
                tabSettings: '⚙️ Settings',
                reciter: '🎤 Reciter',
                surah: '📖 Surah',
                ayahRange: '📍 Ayah Range',
                fromAyah: 'From Ayah',
                toAyah: 'To Ayah',
                estimatedTimePrefix: '⏱️ Estimated time:',
                bgChangeAyah: 'Change background per ayah',
                bgChangeAyahHint: 'Use a different background for each ayah',
                textGlow: 'Text glow',
                textGlowHint: 'Halo effect around text',
                cinematicDim: 'Cinematic vignette',
                cinematicDimHint: 'Soft cinematic darkening',
                advancedOptions: 'Advanced Options',
                fpsLabel: 'Video smoothness (FPS)',
                qualityLabel: 'Video quality',
                aspectRatioLabel: '📐 Aspect ratio',
                quranFontLabel: '✒️ Quran font',
                translationFontLabel: '🔤 Translation font',
                customBgSearch: 'Custom background search',
                bgQueryPlaceholder: 'Type: sea, sky, mountains...',
                random: '🎲 Random',
                generateVideoBtn: '✨ Generate Video',
                stopBtn: '🛑 Stop',
                preparing: 'Preparing...',
                remaining: '⏳ Remaining:',
                download: '⬇️ Download',
                newVideo: '🔄 New Video',
                batchHeader: '📦 Create Video Batch',
                batchSubheader: 'Add videos to the list, then start generation',
                randomReciters: '🎤 Random reciters',
                selectAll: 'Select all',
                deselectAll: 'Clear all',
                addToList: '➕ Add to List',
                batchListTitle: '📋 Video list',
                batchEmpty: 'No videos added yet',
                totalEstimatedPrefix: '⏱️ Total estimated time:',
                startBatchBtn: '🚀 Start Batch',
                videosWord: 'videos',
                cancelBatchBtn: '🛑 Cancel Batch',
                historyTitle: 'Video History',
                clearAll: '🗑️ Clear All',
                noHistory: 'No videos in history',
                preview: '▶️ Preview',
                youtube: '📺 YouTube',
                unavailable: 'Unavailable',
                unspecified: 'Unspecified',
                arabicText: 'Arabic text',
                englishTranslation: 'English translation',
                color: 'Color',
                size: 'Size',
                outlineColor: 'Outline color',
                outlineWidth: 'Outline width',
                pexelsKeyOptional: 'Pexels key (optional)',
                pexelsPlaceholder: 'Leave empty to use default key',
                saveSettingsBtn: '💾 Save Settings',
                restoreDefaultsBtn: 'Restore Defaults',
                processingRunning: 'Processing... ({current}/{total})',
                completed: '✅ Completed!',
                cancelled: '⚠️ Cancelled',
                waiting: '⏳ Waiting...',
                currentVideoPrefix: '🎬',
                remainingTimePrefix: '⏱️ Remaining time:',
                ayahWord: 'Ayah',
                secShort: 's',
                minShort: 'm',
                hourShort: 'h',
                secondWord: 'seconds',
                minuteWord: 'minutes',
                hourWord: 'hours',
                maxAyahOnly: 'This surah has only {max} ayahs',
                loadingConfigFailed: 'Failed to load configuration',
                generationStartFailed: 'Failed to start processing',
                networkError: 'Network connection error',
                processing: 'Processing...',
                unknownError: 'An error occurred',
                videoCreated: 'Video created successfully!',
                stopConfirm: 'Do you want to stop processing?',
                stopDone: 'Processing stopped',
                loadingVideo: 'Loading video...',
                loadingVideoFailed: 'Failed to load video',
                deleteItemConfirm: 'Delete this item?',
                deleted: 'Deleted successfully',
                deleteFailed: 'Delete failed',
                clearHistoryConfirm: 'Clear all history? This cannot be undone.',
                historyCleared: 'History cleared',
                historyClearFailed: 'Failed to clear history',
                settingsSaved: 'Settings saved',
                resetSettingsConfirm: 'Restore default settings?',
                settingsRestored: 'Default settings restored',
                calculating: '⏳ Calculating...',
                maxBatchLimit: 'Maximum is {max} videos per batch',
                alreadyInBatch: 'This video is already in the list',
                addedToBatch: 'Added: {surah} ({reciter})',
                addBatchFirst: 'Add videos to the list first',
                creatingBatch: 'Creating batch...',
                batchCreated: 'Created a batch with {count} videos',
                batchCreateFailed: 'Failed to create batch',
                batchCancelled: 'Batch cancelled',
                batchCreatedDone: 'Successfully created {count} videos!',
                youtubeNotConfigured: '⚠️ YouTube feature is not configured. Contact the developer.',
                youtubeAuthOpening: 'Opening authentication window...',
                youtubeLinked: '✅ YouTube connected successfully!',
                youtubeRedirectHint: '⚠️ You may need to add the Redirect URI in Google Cloud Console',
                youtubeDialogTitle: '📺 Publish to YouTube',
                ytTitleLabel: '📌 Title',
                ytTitlePlaceholder: 'Video title',
                ytDescriptionLabel: '📝 Description',
                ytDescriptionPlaceholder: 'Video description',
                ytTagsLabel: '🏷️ Tags (comma-separated)',
                ytTagsPlaceholder: 'quran, recitation, islam',
                ytPrivacyLabel: '🔒 Privacy',
                ytPrivacyUnlisted: '🔗 Unlisted (share by link)',
                ytPrivacyPrivate: '🔐 Private',
                ytPrivacyPublic: '🌍 Public',
                ytPrivacyScheduled: '📅 Scheduled (public at specific time)',
                ytScheduleLabel: '📆 Scheduled publish time',
                ytScheduleNote: '⚠️ Time should be at least one hour from now',
                ytPublishNow: '📤 Publish now',
                ytSchedulePublish: '📅 Schedule publish',
                ytCancel: 'Cancel',
                ytUploading: '⏳ Uploading... please wait',
                schedulePickTime: '⚠️ Please select a schedule time',
                scheduleMin15: '⚠️ Schedule time must be at least 15 minutes from now',
                scheduledSuccess: '✅ Video scheduled successfully!',
                publishedSuccess: '✅ Video published successfully!',
                youtubeMustConnect: '⚠️ Connect your YouTube account first',
                uploadFailed: 'Upload failed',
                connectionFailed: '❌ Connection failed',
                runningJobResume: '🎬 A video is currently processing!\n📊 Progress: {percent}%\n\nDo you want to resume tracking it?',
                scheduledConfirm: 'Video scheduled successfully!\n\nIt will be published at: {time}\n\nOpen video link?\n{url}',
                publishedConfirm: 'Published successfully!\n\nOpen video link?\n{url}',
                englishShort: 'EN',
                arabicShort: 'AR',
                bgEnhanceLabel: '✨ Background Enhancement',
                bgEnhanceHint: 'Improve background visual quality',
                bgEnhanceSmart: '🌟 Smart enhance (default)',
                bgEnhanceDark: '🌙 Dark background',
                bgEnhanceSaturate: '🎨 Rich colors',
                bgEnhanceNone: '⚪ No effect',
                bannerTitle: 'No Pexels API key',
                bannerTextBefore: '— Videos will use an animated gradient background instead of real videos. Get a free key from',
                bannerTextAfter: 'then paste it here:',
                bannerSave: 'Save',
                bannerDismiss: 'Hide'
            }
        };

        function t(key, vars = {}) {
            let value = (I18N[CURRENT_LANG] && I18N[CURRENT_LANG][key]) || I18N.ar[key] || key;
            Object.entries(vars).forEach(([k, v]) => {
                value = value.replace(`{${k}}`, String(v));
            });
            return value;
        }

        function localeCode() {
            return CURRENT_LANG === 'ar' ? 'ar-EG' : 'en-US';
        }

        function localizeDurationText(raw) {
            if (!raw || CURRENT_LANG === 'ar') return raw;
            return raw
                .replace(/ساعة/g, 'hours')
                .replace(/دقيقة/g, 'minutes')
                .replace(/ثانية/g, 'seconds')
                .replace(/\sس\s/g, ' h ')
                .replace(/\sد\s/g, ' m ')
                .replace(/\sث\s/g, ' s ');
        }

        function localizeStatusText(raw) {
            if (!raw || CURRENT_LANG === 'ar') return raw;
            if (raw.startsWith('جاري التصدير')) return raw.replace('جاري التصدير', 'Exporting');
            if (raw.startsWith('جاري المعالجة')) return raw.replace('جاري المعالجة', 'Processing');
            if (raw.startsWith('Processing Ayah')) return raw;
            return raw;
        }

        function applyLanguage() {
            const html = document.documentElement;
            const isArabic = CURRENT_LANG === 'ar';
            html.lang = CURRENT_LANG;
            html.dir = isArabic ? 'rtl' : 'ltr';

            const langBtn = document.getElementById('langBtn');
            if (langBtn) langBtn.textContent = isArabic ? t('englishShort') : t('arabicShort');
            if (langBtn) langBtn.title = isArabic ? 'Switch to English' : 'التحويل إلى العربية';

            document.title = t('appTitle');

            const appTitle = document.getElementById('appTitle');
            if (appTitle) appTitle.textContent = t('appTitle');
            const appSubtitle = document.getElementById('appSubtitle');
            if (appSubtitle) appSubtitle.textContent = t('appSubtitle');
            const tabMain = document.getElementById('tabMain');
            if (tabMain) tabMain.textContent = t('tabMain');
            const tabBatch = document.getElementById('tabBatch');
            if (tabBatch) tabBatch.textContent = t('tabBatch');
            const tabHistory = document.getElementById('tabHistory');
            if (tabHistory) tabHistory.textContent = t('tabHistory');
            const tabMedia = document.getElementById('tabMedia');
            if (tabMedia) tabMedia.textContent = isArabic ? '🎞️ مكتبة الوسائط' : '🎞️ Media Hub';
            const tabSettings = document.getElementById('tabSettings');
            if (tabSettings) tabSettings.textContent = t('tabSettings');

            const mediaTitle = document.getElementById('mediaHubTitle');
            if (mediaTitle) mediaTitle.textContent = isArabic ? '🎞️ مكتبة الوسائط' : '🎞️ Media Hub';
            const mediaEmptyText = document.getElementById('mediaEmptyText');
            if (mediaEmptyText) mediaEmptyText.textContent = isArabic ? 'لا توجد فيديوهات لهذه التصفية' : 'No videos found for this filter';

            const mediaLabels = isArabic
                ? { all: 'الكل', undownloaded: 'غير مُنزّل', downloaded: 'مُنزّل', failed: 'فاشل', expired: 'منتهي' }
                : { all: 'All', undownloaded: 'Undownloaded', downloaded: 'Downloaded', failed: 'Failed', expired: 'Expired' };
            document.querySelectorAll('#mediaFilters .media-filter-btn').forEach((btn) => {
                const key = btn.dataset.filter;
                if (mediaLabels[key]) btn.textContent = mediaLabels[key];
            });

            const setText = (selector, text) => {
                const el = document.querySelector(selector);
                if (el) el.textContent = text;
            };

            const setAttr = (selector, attr, text) => {
                const el = document.querySelector(selector);
                if (el) el.setAttribute(attr, text);
            };

            const setOptions = (selector, values) => {
                const options = document.querySelectorAll(selector);
                options.forEach((option, idx) => {
                    if (values[idx]) option.textContent = values[idx];
                });
            };

            setText('#mainReciterLabel', t('reciter'));
            setText('#mainSurahLabel', t('surah'));
            setText('#main-panel .ayah-selector-title', t('ayahRange'));

            const mainAyahLabels = document.querySelectorAll('#main-panel .ayah-label');
            if (mainAyahLabels[0]) mainAyahLabels[0].textContent = t('fromAyah');
            if (mainAyahLabels[1]) mainAyahLabels[1].textContent = t('toAyah');

            const maxAyahHint = document.getElementById('maxAyahHint');
            if (maxAyahHint && maxAyahHint.textContent) {
                const currentSurah = parseInt(document.getElementById('surahSelect')?.value || '1');
                const max = VERSE_COUNTS[currentSurah] || 286;
                maxAyahHint.textContent = isArabic ? `(عدد الآيات: ${max})` : `(Ayahs: ${max})`;
            }

            const estNode = document.getElementById('estimatedTimeDisplay');
            if (estNode && estNode.firstChild) {
                estNode.firstChild.textContent = `${t('estimatedTimePrefix')} `;
            }

            setText('#main-panel .toggle-group .toggle-item:nth-child(1) h4', t('bgChangeAyah'));
            setText('#main-panel .toggle-group .toggle-item:nth-child(1) .toggle-info span', t('bgChangeAyahHint'));
            setText('#main-panel .toggle-group .toggle-item:nth-child(2) h4', t('textGlow'));
            setText('#main-panel .toggle-group .toggle-item:nth-child(2) .toggle-info span', t('textGlowHint'));
            setText('#main-panel .toggle-group .toggle-item:nth-child(3) h4', t('cinematicDim'));
            setText('#main-panel .toggle-group .toggle-item:nth-child(3) .toggle-info span', t('cinematicDimHint'));
            setText('#bgEffectLabel', t('bgEnhanceLabel'));
            setText('#bgEffectHint', t('bgEnhanceHint'));
            setOptions('#backgroundEffect option', isArabic
                ? ['🌟 تحسين ذكي (افتراضي)', '🌙 خلفية مظلمة', '🎨 ألوان غنية', '⚪ بدون تأثير']
                : ['🌟 Smart enhance (default)', '🌙 Dark background', '🎨 Rich colors', '⚪ No effect']);
            setText('#batchBgEffectLabel', t('bgEnhanceLabel'));
            setText('#batchBgEffectHint', t('bgEnhanceHint'));
            setOptions('#batchBackgroundEffect option', isArabic
                ? ['🌟 تحسين ذكي (افتراضي)', '🌙 خلفية مظلمة', '🎨 ألوان غنية', '⚪ بدون تأثير']
                : ['🌟 Smart enhance (default)', '🌙 Dark background', '🎨 Rich colors', '⚪ No effect']);
            setText('#bannerTitle', t('bannerTitle'));
            setText('#bannerTextBefore', t('bannerTextBefore'));
            setText('#bannerTextAfter', t('bannerTextAfter'));
            setText('#bannerSaveBtn', t('bannerSave'));
            setText('#bannerDismissBtn', t('bannerDismiss'));
            setText('#main-panel .advanced-toggle span:last-child', t('advancedOptions'));

            setText('#main-panel #advancedOptions .form-group:nth-child(1) .form-label', t('fpsLabel'));
            setText('#main-panel #advancedOptions .form-group:nth-child(2) .form-label', t('qualityLabel'));
            setText('#main-panel #advancedOptions .form-group:nth-child(3) .form-label', t('aspectRatioLabel'));
            setText('#main-panel #advancedOptions .form-group:nth-child(4) .form-label', t('quranFontLabel'));
            setText('#main-panel #advancedOptions .form-group:nth-child(5) .form-label', t('translationFontLabel'));
            setText('#main-panel #advancedOptions .toggle-item .toggle-info h4', t('customBgSearch'));
            setAttr('#bgQuery', 'placeholder', t('bgQueryPlaceholder'));

            setOptions('#fpsSelect option', isArabic
                ? ['🚀 15 FPS - سريع جداً', '⚖️ 20 FPS - متوازن', '🎬 24 FPS - سينمائي', '💎 30 FPS - الأكثر سلاسة']
                : ['🚀 15 FPS - ultra fast', '⚖️ 20 FPS - balanced', '🎬 24 FPS - cinematic', '💎 30 FPS - smoothest']);
            setOptions('#qualitySelect option', isArabic
                ? ['⚡ 720p HD - الأسرع', '🌟 1080p FHD']
                : ['⚡ 720p HD - fastest', '🌟 1080p FHD']);
            setOptions('#aspectRatio option', isArabic
                ? ['📱 9:16 - ريلز / تيك توك', '⬜ 1:1 - سوير / انستجرام', '🖥️ 16:9 - يوتيوب']
                : ['📱 9:16 - Reels / TikTok', '⬜ 1:1 - Square / Instagram', '🖥️ 16:9 - YouTube']);
            setOptions('#fontSelect option', isArabic
                ? ['Arabic - الخط الافتراضي', 'Classic - كلاسيك', 'Amiri - أميري', 'Uthmani - عثماني']
                : ['Arabic - default', 'Classic - classic', 'Amiri - elegant', 'Uthmani - uthmani']);
            setOptions('#fontEnSelect option', isArabic
                ? ['English - الافتراضي', 'Cinzel - كلاسيكي', 'Playfair - أنيق', 'Lora - عصري']
                : ['English - default', 'Cinzel - classic', 'Playfair - elegant', 'Lora - modern']);

            setText('#main-panel .btn-row .btn-secondary', t('random'));
            setText('#submitBtn', t('generateVideoBtn'));
            setText('#stopBtn', t('stopBtn'));

            setText('#progressStatus', t('preparing'));
            const etaNode = document.getElementById('progressEta');
            if (etaNode && etaNode.firstChild) etaNode.firstChild.textContent = `${t('remaining')} `;
            setText('#downloadLink', t('download'));
            setText('#resultSection .result-actions .btn-secondary', t('newVideo'));
            setText('#resultEditBtn', isArabic ? '✏️ تعديل' : '✏️ Edit');
            setText('#resultRegenerateBtn', isArabic ? '♻️ إعادة إنشاء' : '♻️ Regenerate');

            setText('#batch-panel .batch-header h3', t('batchHeader'));
            setText('#batch-panel .batch-header p', t('batchSubheader'));
            setText('#batchReciterLabel', t('reciter'));
            setText('#batchSurahLabel', t('surah'));
            setText('#batch-panel .ayah-selector-title', t('ayahRange'));
            const batchAyahLabels = document.querySelectorAll('#batch-panel .ayah-label');
            if (batchAyahLabels[0]) batchAyahLabels[0].textContent = t('fromAyah');
            if (batchAyahLabels[1]) batchAyahLabels[1].textContent = t('toAyah');

            const batchEstNode = document.getElementById('batchEstimatedTimeDisplay');
            if (batchEstNode && batchEstNode.firstChild) {
                batchEstNode.firstChild.textContent = `${t('estimatedTimePrefix')} `;
            }

            setText('#batch-panel .toggle-group .toggle-item:nth-child(1) h4', t('bgChangeAyah'));
            setText('#batch-panel .toggle-group .toggle-item:nth-child(1) .toggle-info span', t('bgChangeAyahHint'));
            setText('#batch-panel .toggle-group .toggle-item:nth-child(2) h4', t('textGlow'));
            setText('#batch-panel .toggle-group .toggle-item:nth-child(3) h4', t('cinematicDim'));
            setText('#batch-panel #batchAdvancedOptions .form-group:nth-child(1) .form-label', t('fpsLabel'));
            setText('#batch-panel #batchAdvancedOptions .form-group:nth-child(2) .form-label', t('qualityLabel'));
            setText('#batch-panel #batchAdvancedOptions .form-group:nth-child(3) .form-label', t('aspectRatioLabel'));
            setText('#batch-panel #batchAdvancedOptions .form-group:nth-child(4) .form-label', t('quranFontLabel'));
            setText('#batch-panel #batchAdvancedOptions .form-group:nth-child(5) .form-label', t('translationFontLabel'));
            setText('#batch-panel #batchAdvancedOptions .toggle-item .toggle-info h4', t('customBgSearch'));
            setAttr('#batchBgQuery', 'placeholder', t('bgQueryPlaceholder'));

            setOptions('#batchFpsSelect option', isArabic
                ? ['🚀 15 FPS - سريع جداً', '⚖️ 20 FPS - متوازن', '🎬 24 FPS - سينمائي', '💎 30 FPS - الأكثر سلاسة']
                : ['🚀 15 FPS - ultra fast', '⚖️ 20 FPS - balanced', '🎬 24 FPS - cinematic', '💎 30 FPS - smoothest']);
            setOptions('#batchQualitySelect option', isArabic
                ? ['⚡ 720p HD - الأسرع', '🌟 1080p FHD']
                : ['⚡ 720p HD - fastest', '🌟 1080p FHD']);
            setOptions('#batchAspectRatio option', isArabic
                ? ['📱 9:16 - ريلز / تيك توك', '⬜ 1:1 - سوير / انستجرام', '🖥️ 16:9 - يوتيوب']
                : ['📱 9:16 - Reels / TikTok', '⬜ 1:1 - Square / Instagram', '🖥️ 16:9 - YouTube']);
            setOptions('#batchFontSelect option', isArabic
                ? ['Arabic - الخط الافتراضي', 'Classic - كلاسيك', 'Amiri - أميري', 'Uthmani - عثماني']
                : ['Arabic - default', 'Classic - classic', 'Amiri - elegant', 'Uthmani - uthmani']);
            setOptions('#batchFontEnSelect option', isArabic
                ? ['English - الافتراضي', 'Cinzel - كلاسيكي', 'Playfair - أنيق', 'Lora - عصري']
                : ['English - default', 'Cinzel - classic', 'Playfair - elegant', 'Lora - modern']);

            setText('#batch-panel .advanced-toggle span:last-child', t('advancedOptions'));
            setText('#batch-panel .form-group[style*="margin-top: 16px"] .form-label', t('randomReciters'));
            setText('#batch-panel #reciterFilterSection .btn-secondary:nth-child(1)', t('selectAll'));
            setText('#batch-panel #reciterFilterSection .btn-secondary:nth-child(2)', t('deselectAll'));
            setText('#batch-panel .btn-row .btn-secondary', t('random'));

            const batchPrimaryButtons = document.querySelectorAll('#batch-panel .btn-primary');
            if (batchPrimaryButtons[0]) batchPrimaryButtons[0].textContent = t('addToList');
            if (batchPrimaryButtons[1]) {
                const totalCount = document.getElementById('batchTotalVideos')?.textContent || '0';
                batchPrimaryButtons[1].innerHTML = isArabic
                    ? `${t('startBatchBtn')} (<span id="batchTotalVideos">${totalCount}</span> ${t('videosWord')})`
                    : `${t('startBatchBtn')} (<span id="batchTotalVideos">${totalCount}</span> ${t('videosWord')})`;
            }

            setText('#batch-panel .history-header h4', `${t('batchListTitle')} (${document.getElementById('batchCount')?.textContent || '0'}/10)`);
            setText('#batch-panel .history-header .btn-secondary', t('clearAll'));
            setText('#batchListEmpty p', t('batchEmpty'));

            const batchTotalNode = document.getElementById('batchTotalTimeDisplay');
            if (batchTotalNode && batchTotalNode.firstChild) batchTotalNode.firstChild.textContent = `${t('totalEstimatedPrefix')} `;
            setText('#batchProgressStatus', t('preparing'));
            const batchRemNode = document.getElementById('batchRemainingTime');
            if (batchRemNode && batchRemNode.firstChild) batchRemNode.firstChild.textContent = `${t('remainingTimePrefix')} `;
            setText('#batchStatusSection .btn-stop', t('cancelBatchBtn'));

            setText('#history-panel .history-header h3', t('historyTitle'));
            setText('#history-panel .history-header .btn-secondary', t('clearAll'));
            setText('#historyEmpty p', t('noHistory'));

            setText('#settings-panel .settings-section:nth-of-type(2) h4', t('arabicText'));
            setText('#settings-panel .settings-section:nth-of-type(3) h4', t('englishTranslation'));
            setText('#settings-panel .settings-section:nth-of-type(4) h4', t('pexelsKeyOptional'));
            setAttr('#pexelsKey', 'placeholder', t('pexelsPlaceholder'));

            document.querySelectorAll('#settings-panel .settings-section:nth-of-type(2) .settings-label').forEach((el, i) => {
                const labels = [t('color'), t('size'), t('outlineColor'), t('outlineWidth')];
                el.textContent = labels[i] || el.textContent;
            });
            document.querySelectorAll('#settings-panel .settings-section:nth-of-type(3) .settings-label').forEach((el, i) => {
                const labels = [t('color'), t('size'), t('outlineColor'), t('outlineWidth')];
                el.textContent = labels[i] || el.textContent;
            });

            setText('#settings-panel .btn-primary', t('saveSettingsBtn'));
            setText('#settings-panel .btn-secondary', t('restoreDefaultsBtn'));

            const estValue = document.getElementById('estimatedTime');
            if (estValue) estValue.textContent = localizeDurationText(estValue.textContent);
            const batchEstValue = document.getElementById('batchEstimatedTime');
            if (batchEstValue) batchEstValue.textContent = localizeDurationText(batchEstValue.textContent);
            const batchTotal = document.getElementById('batchTotalTime');
            if (batchTotal) batchTotal.textContent = localizeDurationText(batchTotal.textContent);
        }

        async function toggleLanguage() {
            CURRENT_LANG = CURRENT_LANG === 'ar' ? 'en' : 'ar';
            localStorage.setItem('quran_ui_lang', CURRENT_LANG);
            await loadConfig();
            applyLanguage();
            initBatchPage();
            renderBatchList();
            loadHistory();
            updateEstimatedTime();
            updateBatchEstimatedTime();
            updateBatchTotalTime();
        }

        const defaultSettings = {
            arColor: '#ffffff',
            arHighlightColor: '#ffd700',
            arSize: '1',
            arOutlineColor: '#000000',
            arOutlineWidth: '4',
            enColor: '#FFD700',
            enSize: '1',
            enOutlineColor: '#000000',
            enOutlineWidth: '3'
        };

        // ✅ إعدادات الفيديو الافتراضية
        const defaultVideoSettings = {
            fontSelect: 'Arabic',
            fontEnSelect: 'English',
            translationLang: 'en',
            wordHighlight: false,
            fpsSelect: '20',
            qualitySelect: '720',
            aspectRatio: '9:16',
            dynamicBg: true,
            useGlow: true,
            useVignette: true,
            scenePack: 'nature_calm',
            bgCrossfadeSec: '0.5',
            adaptiveTextContrast: true,
            safeAreaGuides: false,
            safeAreaPaddingPx: '48',
            audioProfile: 'studio',
            audioDenoise: false,
            audioDeEss: false
        };

        // ✅ حفظ إعدادات الفيديو
        function saveVideoSettings() {
            const settings = {
                fontSelect: document.getElementById('fontSelect')?.value || 'Arabic',
                fontEnSelect: document.getElementById('fontEnSelect')?.value || 'English',
                translationLang: document.getElementById('translationLang')?.value || 'en',
                wordHighlight: document.getElementById('wordHighlight')?.checked ?? false,
                fpsSelect: document.getElementById('fpsSelect')?.value || '20',
                qualitySelect: document.getElementById('qualitySelect')?.value || '720',
                aspectRatio: document.getElementById('aspectRatio')?.value || '9:16',
                dynamicBg: document.getElementById('dynamicBg')?.checked ?? true,
                useGlow: document.getElementById('useGlow')?.checked ?? true,
                useVignette: document.getElementById('useVignette')?.checked ?? true,
                scenePack: document.getElementById('scenePack')?.value || 'nature_calm',
                bgCrossfadeSec: document.getElementById('bgCrossfadeSec')?.value || '0.5',
                adaptiveTextContrast: document.getElementById('adaptiveTextContrast')?.checked ?? true,
                safeAreaGuides: document.getElementById('safeAreaGuides')?.checked ?? false,
                safeAreaPaddingPx: document.getElementById('safeAreaPaddingPx')?.value || '48',
                audioProfile: document.getElementById('audioProfile')?.value || 'studio',
                audioDenoise: document.getElementById('audioDenoise')?.checked ?? false,
                audioDeEss: document.getElementById('audioDeEss')?.checked ?? false
            };
            localStorage.setItem('quran_video_settings', JSON.stringify(settings));
        }

        // ✅ تحميل إعدادات الفيديو
        function loadVideoSettings() {
            const saved = JSON.parse(localStorage.getItem('quran_video_settings')) || defaultVideoSettings;

            Object.entries(saved).forEach(([key, value]) => {
                const el = document.getElementById(key);
                if (el) {
                    if (el.type === 'checkbox') {
                        el.checked = value;
                    } else {
                        el.value = value;
                    }
                }
            });
        }

        // ✅ حفظ تلقائي عند تغيير أي إعداد
        function initVideoSettingsAutoSave() {
            const settingsIds = ['fontSelect', 'fontEnSelect', 'fpsSelect', 'qualitySelect', 'aspectRatio', 'dynamicBg', 'useGlow', 'useVignette', 'scenePack', 'bgCrossfadeSec', 'adaptiveTextContrast', 'safeAreaGuides', 'safeAreaPaddingPx', 'audioProfile', 'audioDenoise', 'audioDeEss'];
            settingsIds.forEach(id => {
                const el = document.getElementById(id);
                if (el) {
                    el.addEventListener('change', () => {
                        saveVideoSettings();
                    });
                }
            });
        }

        // ═══════════════════════════════════════
        // 🔑 Session Management
        // ═══════════════════════════════════════
        function getOrCreateSessionId() {
            let sessionId = localStorage.getItem('quran_session_id');
            const sessionAge = localStorage.getItem('quran_session_age');
            const thirtyDays = 30 * 24 * 60 * 60 * 1000;
            
            if (!sessionId || !sessionAge || (Date.now() - parseInt(sessionAge)) > thirtyDays) {
                sessionId = 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                localStorage.setItem('quran_session_id', sessionId);
                localStorage.setItem('quran_session_age', Date.now().toString());
                console.log('🆕 New session created:', sessionId);
            }
            
            return sessionId;
        }

        // ═══════════════════════════════════════
        // 🚀 Initialization
        // ═══════════════════════════════════════
        window.onload = async () => {
            SESSION_ID = getOrCreateSessionId();
            console.log('📱 Session ID:', SESSION_ID);

            applyLanguage();

            initTabs();
            loadSettings();
            loadVideoSettings();  // ✅ تحميل إعدادات الفيديو
            initVideoSettingsAutoSave();  // ✅ حفظ تلقائي

            // تحميل الكونفج الأول عشان VERSE_COUNTS
            await loadConfig();
            
            // بعدين نعمل validation بعد ما البيانات تتحمل
            initAyahValidation();
            
            await loadHistory();
            await loadMediaHub(mediaHubFilter);
            await checkRunningJob();
            
            // تحديث الوقت التقريبي عند التحميل
            setTimeout(() => {
                updateEstimatedTime();
                updateBatchEstimatedTime();
            }, 500);
        };

        function initAyahValidation() {
            const startInput = document.getElementById('startAyah');
            const endInput = document.getElementById('endAyah');
            const surahInput = document.getElementById('surahSelect');
            const maxHint = document.getElementById('maxAyahHint');
            
            // تحديث الحد الأقصى عند تغيير السورة
            const updateMaxAyah = () => {
                const surah = parseInt(surahInput?.value) || 1;
                const max = VERSE_COUNTS[surah] || 286;
                
                // تحديث الـ max attribute
                if (startInput) startInput.max = max;
                if (endInput) endInput.max = max;
                
                // عرض تلميح الحد الأقصى
                if (maxHint) maxHint.textContent = CURRENT_LANG === 'ar' ? `(عدد الآيات: ${max})` : `(Ayahs: ${max})`;
                
                // تصحيح القيم الحالية
                if (parseInt(startInput?.value) > max) startInput.value = 1;
                if (parseInt(endInput?.value) > max) endInput.value = Math.min(5, max);
            };
            
            // التحقق الفوري أثناء الكتابة
            const validateOnInput = (input) => {
                const surah = parseInt(surahInput?.value) || 1;
                const max = VERSE_COUNTS[surah] || 286;
                let val = parseInt(input.value) || 1;
                
                if (val < 1) input.value = 1;
                if (val > max) {
                    input.value = max;
                    showToast(t('maxAyahOnly', { max }), 'error');
                }
            };
            
            startInput?.addEventListener('input', () => validateOnInput(startInput));
            endInput?.addEventListener('input', () => validateOnInput(endInput));
            
            startInput?.addEventListener('blur', () => validateAyahInput('startAyah'));
            endInput?.addEventListener('blur', () => validateAyahInput('endAyah'));
            
            startInput?.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    validateAyahInput('startAyah');
                    endInput.focus();
                }
            });
            
            endInput?.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    validateAyahInput('endAyah');
                }
            });
            
            surahInput?.addEventListener('change', () => {
                updateMaxAyah();
                const max = VERSE_COUNTS[parseInt(surahInput.value)] || 286;
                startInput.value = 1;
                endInput.value = Math.min(5, max);
                validateAyahRange();
            });
            
            // تحديث الحد الأقصى عند تحميل البيانات
            setTimeout(updateMaxAyah, 500);
        }

        function initTabs() {
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const tabId = btn.dataset.tab;
                    
                    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
                    
                    btn.classList.add('active');
                    document.getElementById(`${tabId}-panel`).classList.add('active');

                    if (tabId === 'history') {
                        loadHistory();
                    } else if (tabId === 'media') {
                        loadMediaHub(mediaHubFilter);
                    }
                });
            });
        }

        async function loadConfig() {
            try {
                const res = await fetch(`/api/config?lang=${encodeURIComponent(CURRENT_LANG)}`);
                const data = await res.json();
                VERSE_COUNTS = data.verseCounts;

                const prevSurahValue = surahSelect.value;
                const prevReciterValue = reciterSelect.value;

                surahSelect.innerHTML = '';
                reciterSelect.innerHTML = '';
                
                data.surahs.forEach((name, i) => {
                    surahSelect.add(new Option(`${i + 1}. ${name}`, i + 1));
                });
                
                Object.entries(data.reciters).forEach(([name, id]) => {
                    reciterSelect.add(new Option(name, id));
                });

                if (prevSurahValue) {
                    surahSelect.value = prevSurahValue;
                }
                if (prevReciterValue) {
                    reciterSelect.value = prevReciterValue;
                }
                
                // تحديث الحد الأقصى للآيات بناءً على السورة الأولى
                const firstSurahMax = VERSE_COUNTS[1] || 7;
                const startAyahInput = document.getElementById('startAyah');
                const endAyahInput = document.getElementById('endAyah');
                
                if (startAyahInput) startAyahInput.max = firstSurahMax;
                if (endAyahInput) endAyahInput.max = firstSurahMax;
                
                // إضافة event listener لتحديث الحد الأقصى عند تغيير السورة
                surahSelect.addEventListener('change', function() {
                    const surah = parseInt(this.value) || 1;
                    const max = VERSE_COUNTS[surah] || 286;
                    
                    if (startAyahInput) {
                        startAyahInput.max = max;
                        if (parseInt(startAyahInput.value) > max) startAyahInput.value = 1;
                    }
                    
                    if (endAyahInput) {
                        endAyahInput.max = max;
                        if (parseInt(endAyahInput.value) > max) endAyahInput.value = Math.min(5, max);
                    }
                    
                    // تحديث الوقت التقريبي
                    updateEstimatedTime();
                });
                
                // تحديث الوقت التقريبي
                updateEstimatedTime();
                
            } catch (err) {
                console.error('Config load error:', err);
                showToast(t('loadingConfigFailed'), 'error');
            }
        }

        // ═══════════════════════════════════════
        // 📝 Form Handling
        // ═══════════════════════════════════════
        document.getElementById('videoForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            await startGeneration();
        });

        function adjustAyah(id, delta) {
            const input = document.getElementById(id);
            const surah = parseInt(surahSelect.value);
            const max = VERSE_COUNTS[surah] || 286;
            let val = parseInt(input.value) + delta;
            
            if (val < 1) val = 1;
            if (val > max) val = max;
            input.value = val;
            
            validateAyahRange();
        }

        function validateAyahInput(id) {
            const input = document.getElementById(id);
            const surah = parseInt(surahSelect.value);
            const max = VERSE_COUNTS[surah] || 286;
            let val = parseInt(input.value);
            
            if (isNaN(val) || val < 1) {
                val = 1;
            }
            if (val > max) {
                val = max;
                showToast(t('maxAyahOnly', { max }), 'error');
            }
            
            input.value = val;
            validateAyahRange();
        }

        function validateAyahRange() {
            const surah = parseInt(surahSelect.value);
            const max = VERSE_COUNTS[surah] || 286;
            const start = parseInt(startAyah.value);
            const end = parseInt(endAyah.value);
            
            if (start > end) {
                endAyah.value = start;
            }
            
            if (end > max) {
                endAyah.value = max;
            }
            
            // تحديث الوقت التقريبي
            updateEstimatedTime();
        }

        // ═══════════════════════════════════════
        // ⏱️ Estimated Time Calculator (Real Duration from API)
        // ═══════════════════════════════════════
        
        // Cache لتخزين مدة الآيات
        let durationCache = {};

        async function fetchEstimatedTime(reciter, surah, startAyah, endAyah) {
            // إنشاء مفتاح للـ cache
            const cacheKey = `${reciter}-${surah}-${startAyah}-${endAyah}`;
            
            // لو موجود في الـ cache
            if (durationCache[cacheKey]) {
                return durationCache[cacheKey];
            }
            
            try {
                const res = await fetch('/api/estimate-duration', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ reciter, surah, startAyah, endAyah, lang: CURRENT_LANG })
                });
                
                const data = await res.json();
                
                if (data.ok) {
                    // حفظ في الـ cache
                    durationCache[cacheKey] = data;
                    return data;
                }
            } catch (err) {
                console.error('Duration fetch error:', err);
            }
            
            return null;
        }

        function updateEstimatedTime() {
            const reciter = document.getElementById('reciterSelect')?.value;
            const surah = parseInt(document.getElementById('surahSelect')?.value) || 1;
            const start = parseInt(document.getElementById('startAyah')?.value) || 1;
            const end = parseInt(document.getElementById('endAyah')?.value) || 1;
            const el = document.getElementById('estimatedTime');
            
            if (el) {
                el.textContent = t('calculating');
            }
            
            fetchEstimatedTime(reciter, surah, start, end).then(data => {
                if (data && data.formatted) {
                    if (el) {
                        el.textContent = localizeDurationText(data.formatted);
                    }
                } else {
                    if (el) {
                        el.textContent = '--:--';
                    }
                }
            });
        }

        function updateBatchEstimatedTime() {
            const reciter = document.getElementById('batchReciterSelect')?.value;
            const surah = parseInt(document.getElementById('batchSurahSelect')?.value) || 1;
            const start = parseInt(document.getElementById('batchStartAyah')?.value) || 1;
            const end = parseInt(document.getElementById('batchEndAyah')?.value) || 1;
            const el = document.getElementById('batchEstimatedTime');
            
            if (el) {
                el.textContent = t('calculating');
            }
            
            fetchEstimatedTime(reciter, surah, start, end).then(data => {
                if (data && data.formatted) {
                    if (el) {
                        el.textContent = localizeDurationText(data.formatted);
                    }
                } else {
                    if (el) {
                        el.textContent = '--:--';
                    }
                }
            });
        }

        async function updateBatchTotalTime() {
            // حساب الوقت الكلي لكل الفيديوهات في القائمة
            const totalTimeDisplay = document.getElementById('batchTotalTimeDisplay');
            const totalTimeEl = document.getElementById('batchTotalTime');
            
            if (batchItems.length === 0) {
                if (totalTimeDisplay) totalTimeDisplay.style.display = 'none';
                return;
            }
            
            if (totalTimeDisplay) totalTimeDisplay.style.display = 'block';
            if (totalTimeEl) totalTimeEl.textContent = t('calculating');
            
            let totalMs = 0;
            
            for (const item of batchItems) {
                const data = await fetchEstimatedTime(item.reciter, item.surah, item.startAyah, item.endAyah);
                if (data && data.durationMs) {
                    totalMs += data.durationMs;
                }
            }
            
            const totalSeconds = totalMs / 1000;
            if (totalTimeEl) {
                if (totalSeconds > 0) {
                    totalTimeEl.textContent = localizeDurationText(formatDurationLocal(totalSeconds));
                } else {
                    totalTimeEl.textContent = '--:--';
                }
            }
        }

        function formatDurationLocal(seconds) {
            if (seconds < 60) {
                return `${Math.round(seconds)} ${CURRENT_LANG === 'ar' ? t('secondWord') : t('secShort')}`;
            } else if (seconds < 3600) {
                const mins = Math.floor(seconds / 60);
                const secs = Math.round(seconds % 60);
                if (secs > 0) {
                    return `${mins} ${t('minShort')} ${secs} ${t('secShort')}`;
                }
                return `${mins} ${CURRENT_LANG === 'ar' ? t('minuteWord') : t('minShort')}`;
            } else {
                const hours = Math.floor(seconds / 3600);
                const mins = Math.floor((seconds % 3600) / 60);
                if (mins > 0) {
                    return `${hours} ${t('hourShort')} ${mins} ${t('minShort')}`;
                }
                return `${hours} ${CURRENT_LANG === 'ar' ? t('hourWord') : t('hourShort')}`;
            }
        }

        function randomize() {
            if (reciterSelect.options.length > 0) {
                reciterSelect.selectedIndex = Math.floor(Math.random() * reciterSelect.options.length);
            }
            if (surahSelect.options.length > 0) {
                surahSelect.selectedIndex = Math.floor(Math.random() * surahSelect.options.length);
                // تحديث الـ max attribute للآيات بعد تغيير السورة
                surahSelect.dispatchEvent(new Event('change'));
                const max = VERSE_COUNTS[parseInt(surahSelect.value)] || 286;
                const start = Math.floor(Math.random() * Math.max(1, max - 5)) + 1;
                startAyah.value = start;
                endAyah.value = Math.min(start + 4, max);
            }
            updateEstimatedTime();
        }

        function toggleAdvanced() {
            const options = document.getElementById('advancedOptions');
            options.classList.toggle('show');
        }

        function toggleBatchAdvanced() {
            const options = document.getElementById('batchAdvancedOptions');
            options.classList.toggle('show');
        }

        function toggleBatchSearchInput() {
            const input = document.getElementById('batchSearchInputGroup');
            const checkbox = document.getElementById('batchUseSearch');
            input.style.display = checkbox.checked ? 'block' : 'none';
        }

        function toggleSearchInput() {
            const input = document.getElementById('searchInputGroup');
            input.style.display = useSearch.checked ? 'block' : 'none';
        }

        // ═══════════════════════════════════════
        // 🎬 Video Generation
        // ═══════════════════════════════════════
        async function startGeneration() {
            const style = getStyleSettings();
            
            const payload = {
                sessionId: SESSION_ID,
                lang: CURRENT_LANG,
                reciter: reciterSelect.value,
                surah: parseInt(surahSelect.value),
                startAyah: parseInt(startAyah.value),
                endAyah: parseInt(endAyah.value),
                fps: parseInt(fpsSelect.value),
                quality: qualitySelect.value,
                aspectRatio: document.getElementById('aspectRatio').value || '9:16',
                font: document.getElementById('fontSelect').value || 'Arabic',
                fontEn: document.getElementById('fontEnSelect').value || 'English',
                translationLang: document.getElementById('translationLang')?.value || 'en',
                wordHighlight: document.getElementById('wordHighlight')?.checked ?? false,
                dynamicBg: dynamicBg.checked,
                useGlow: useGlow.checked,
                useVignette: useVignette.checked,
                bgQuery: useSearch.checked ? bgQuery.value : '',
                backgroundEffect: document.getElementById('backgroundEffect')?.value || 'enhance',
                scenePack: document.getElementById('scenePack')?.value || 'nature_calm',
                bgCrossfadeSec: parseFloat(document.getElementById('bgCrossfadeSec')?.value || '0.5'),
                adaptiveTextContrast: document.getElementById('adaptiveTextContrast')?.checked ?? true,
                safeAreaGuides: document.getElementById('safeAreaGuides')?.checked ?? false,
                safeAreaPaddingPx: parseInt(document.getElementById('safeAreaPaddingPx')?.value || '48'),
                audioProfile: document.getElementById('audioProfile')?.value || 'studio',
                audioDenoise: document.getElementById('audioDenoise')?.checked ?? false,
                audioDeEss: document.getElementById('audioDeEss')?.checked ?? false,
                pexelsKey: localStorage.getItem('user_pexels_key') || '',
                style: style
            };

            try {
                const res = await fetch('/api/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                const data = await res.json();
                
                if (data.ok) {
                    currentJobId = data.jobId;
                    currentResultJobId = data.jobId;
                    showProgress();
                    startPolling(data.jobId);
                } else {
                    showToast(t('generationStartFailed'), 'error');
                }
            } catch (err) {
                console.error('Generation error:', err);
                showToast(t('networkError'), 'error');
            }
        }

        function showProgress() {
            document.getElementById('videoForm').style.display = 'none';
            document.getElementById('progressSection').classList.add('active');
            document.getElementById('resultSection').classList.remove('active');
        }

        function startPolling(jobId) {
            if (pollInterval) clearInterval(pollInterval);
            
            pollInterval = setInterval(async () => {
                try {
                    const res = await fetch(`/api/progress?jobId=${encodeURIComponent(jobId)}&sessionId=${encodeURIComponent(SESSION_ID)}`);
                    const data = await res.json();
                    
                    updateProgress(data);
                    
                    if (data.status === 'complete') {
                        clearInterval(pollInterval);
                        showResult(data);
                    } else if (data.status === 'error' || data.status === 'cancelled') {
                        clearInterval(pollInterval);
                        showToast(data.error || t('unknownError'), 'error');
                        resetForm();
                    }
                } catch (err) {
                    console.error('Poll error:', err);
                }
            }, 1500);
        }

        function updateProgress(data) {
            const percent = data.percent || 0;
            const circle = document.getElementById('progressCircle');
            const circumference = 2 * Math.PI * 65;
            
            circle.style.strokeDashoffset = circumference - (percent / 100) * circumference;
            document.getElementById('progressPercent').textContent = `${percent}%`;
            document.getElementById('progressStatus').textContent = localizeStatusText(data.status) || t('processing');
            
            if (data.eta && data.eta !== '--:--') {
                document.getElementById('progressEta').style.display = 'block';
                document.getElementById('etaTime').textContent = data.eta;
            }
        }

        function showResult(data) {
            document.getElementById('progressSection').classList.remove('active');
            document.getElementById('resultSection').classList.add('active');
            
            const videoUrl = data.download_url || `/api/download?jobId=${currentJobId}`;
            document.getElementById('videoPlayer').src = sessionScopedUrl(videoUrl);
            const downloadLinkEl = document.getElementById('downloadLink');
            downloadLinkEl.href = trackedDownloadUrl(videoUrl);
            downloadLinkEl.onclick = () => { refreshMediaViewsLater(); };
            currentResultJobId = currentJobId;
            currentResultConfig = null;
            refreshStorageInfo();
            
            loadHistory();
            loadMediaHub(mediaHubFilter);
            showToast(t('videoCreated'), 'success');
        }

        function sessionScopedUrl(url) {
            if (!url) return '#';
            if (url.includes('sessionId=')) return url;
            const sep = url.includes('?') ? '&' : '?';
            return `${url}${sep}sessionId=${encodeURIComponent(SESSION_ID)}`;
        }

        function trackedDownloadUrl(url, jobId = null) {
            if (!url) return '#';
            const scopedUrl = sessionScopedUrl(url);
            if (scopedUrl.includes('track=')) return scopedUrl;
            const sep = scopedUrl.includes('?') ? '&' : '?';
            return `${scopedUrl}${sep}track=1`;
        }

        function refreshMediaViewsLater() {
            setTimeout(() => {
                loadHistory();
                loadMediaHub(mediaHubFilter);
            }, 1000);
        }

        function resetForm() {
            document.getElementById('videoForm').style.display = 'block';
            document.getElementById('progressSection').classList.remove('active');
            document.getElementById('resultSection').classList.remove('active');
            document.getElementById('progressCircle').style.strokeDashoffset = 408;
            document.getElementById('progressPercent').textContent = '0%';
            currentJobId = null;
        }

        function _parseCreatedAtToUnix(value, fallbackTs = null) {
            if (typeof fallbackTs === 'number' && !Number.isNaN(fallbackTs)) {
                return fallbackTs;
            }
            if (typeof value === 'number' && !Number.isNaN(value)) {
                return value;
            }
            if (typeof value === 'string') {
                const asNum = Number(value);
                if (!Number.isNaN(asNum) && asNum > 0) {
                    return asNum;
                }
                const parsed = Date.parse(value);
                if (!Number.isNaN(parsed)) {
                    return Math.floor(parsed / 1000);
                }
            }
            return Math.floor(Date.now() / 1000);
        }

        async function refreshStorageInfo() {
            const el = document.getElementById('resultStoragePath');
            if (!el) return;
            const fallback = CURRENT_LANG === 'ar'
                ? 'يتم حفظ النسخة الأصلية داخل مجلد outputs، ونسخة التحميل تذهب إلى Downloads في المتصفح.'
                : 'Original file is stored in the app outputs folder, and downloaded copies go to your browser Downloads.';
            el.textContent = fallback;
            try {
                const res = await fetch('/api/storage-info');
                const data = await res.json();
                if (data && data.ok && data.outputsDir) {
                    const prefix = CURRENT_LANG === 'ar' ? 'مسار حفظ الفيديوهات داخل التطبيق: ' : 'App video storage path: ';
                    el.textContent = `${prefix}${data.outputsDir}`;
                }
            } catch (_) {
                // Keep fallback text.
            }
        }

        async function loadJobConfig(jobId) {
            const res = await fetch(`/api/job-config?jobId=${encodeURIComponent(jobId)}&sessionId=${encodeURIComponent(SESSION_ID)}`);
            const data = await res.json();
            if (!data.ok || !data.config) {
                throw new Error(data.error || 'Config unavailable');
            }
            return data.config;
        }

        function applyConfigToMainForm(config) {
            if (!config) return;

            const setValue = (id, value) => {
                const el = document.getElementById(id);
                if (!el || value === undefined || value === null) return;
                el.value = value;
            };
            const setChecked = (id, value) => {
                const el = document.getElementById(id);
                if (!el || value === undefined || value === null) return;
                el.checked = !!value;
            };

            setValue('reciterSelect', config.reciter);
            setValue('surahSelect', config.surah);

            const surahEl = document.getElementById('surahSelect');
            if (surahEl) surahEl.dispatchEvent(new Event('change'));

            setValue('startAyah', config.startAyah);
            setValue('endAyah', config.endAyah);
            setValue('fpsSelect', config.fps);
            setValue('qualitySelect', config.quality);
            setValue('aspectRatio', config.aspectRatio || '9:16');
            setValue('fontSelect', config.font || 'Arabic');
            setValue('fontEnSelect', config.fontEn || 'English');
            setValue('backgroundEffect', config.backgroundEffect || 'enhance');
            setValue('scenePack', config.scenePack || 'nature_calm');
            setValue('bgCrossfadeSec', config.bgCrossfadeSec ?? '0.5');
            setValue('audioProfile', config.audioProfile || 'studio');
            setValue('safeAreaPaddingPx', config.safeAreaPaddingPx ?? '48');

            setChecked('dynamicBg', config.dynamicBg);
            setChecked('useGlow', config.useGlow);
            setChecked('useVignette', config.useVignette);
            setChecked('adaptiveTextContrast', config.adaptiveTextContrast);
            setChecked('safeAreaGuides', config.safeAreaGuides);
            setChecked('audioDenoise', config.audioDenoise);
            setChecked('audioDeEss', config.audioDeEss);

            const query = (config.bgQuery || '').trim();
            const useSearchBox = document.getElementById('useSearch');
            const bgQueryEl = document.getElementById('bgQuery');
            if (useSearchBox) useSearchBox.checked = query.length > 0;
            if (bgQueryEl) bgQueryEl.value = query;
            toggleSearchInput();

            updatePreview();
            validateAyahRange();
        }

        async function openVideoEditor(jobId, autoRegenerate = false) {
            try {
                const config = await loadJobConfig(jobId);
                currentResultConfig = config;
                currentResultJobId = jobId;
                applyConfigToMainForm(config);
                document.querySelector('[data-tab="main"]').click();
                showToast(CURRENT_LANG === 'ar' ? 'تم تحميل الإعدادات للتعديل' : 'Settings loaded for editing', 'success');

                if (autoRegenerate) {
                    await startGeneration();
                }
            } catch (err) {
                console.error('Failed to load job config:', err);
                showToast(CURRENT_LANG === 'ar' ? 'تعذر تحميل إعدادات الفيديو' : 'Could not load video settings', 'error');
            }
        }

        function editCurrentVideo() {
            if (!currentResultJobId) {
                showToast(CURRENT_LANG === 'ar' ? 'لا يوجد فيديو محدد للتعديل' : 'No video selected to edit', 'error');
                return;
            }
            openVideoEditor(currentResultJobId, false);
        }

        function regenerateCurrentVideo() {
            if (!currentResultJobId) {
                showToast(CURRENT_LANG === 'ar' ? 'لا يوجد فيديو لإعادة الإنشاء' : 'No video available to regenerate', 'error');
                return;
            }
            openVideoEditor(currentResultJobId, true);
        }

        async function stopGeneration() {
            if (!currentJobId) return;
            
            if (confirm(t('stopConfirm'))) {
                clearInterval(pollInterval);
                
                await fetch('/api/cancel', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ jobId: currentJobId, sessionId: SESSION_ID })
                });
                
                resetForm();
                showToast(t('stopDone'), 'error');
            }
        }

        // ═══════════════════════════════════════
        // 📜 History
        // ═══════════════════════════════════════
        async function loadHistory() {
            try {
                const res = await fetch(`/api/history?sessionId=${encodeURIComponent(SESSION_ID)}`);
                const data = await res.json();
                
                const list = document.getElementById('historyList');
                const empty = document.getElementById('historyEmpty');
                
                if (data.ok && data.history && data.history.length > 0) {
                    empty.style.display = 'none';
                    list.innerHTML = data.history.map(item => createHistoryItem(item)).join('');
                } else {
                    empty.style.display = 'block';
                    list.innerHTML = '';
                }
            } catch (err) {
                console.error('History load error:', err);
            }
        }

        function createHistoryItem(item) {
            const createdAtUnix = _parseCreatedAtToUnix(item.createdAt, item.createdAtTs);
            const date = new Date(createdAtUnix * 1000);
            const dateStr = date.toLocaleDateString(localeCode()) + ' ' + date.toLocaleTimeString(localeCode(), { hour: '2-digit', minute: '2-digit' });
            
            const now = Date.now() / 1000;
            const remaining = Math.max(0, 43200 - (now - createdAtUnix)); // 12 ساعة = 43200 ثانية
            
            // تنسيق الوقت الذكي
            function formatRemaining(secs) {
                if (secs < 60) return `${secs} ${t('secShort')}`;
                if (secs < 3600) return `${Math.floor(secs / 60)} ${t('minShort')}`;
                const hours = Math.floor(secs / 3600);
                const mins = Math.floor((secs % 3600) / 60);
                return mins > 0 ? `${hours} ${t('hourShort')} ${mins} ${t('minShort')}` : `${hours} ${t('hourShort')}`;
            }
            
            let timerHtml = '';
            if (item.status === 'complete' && remaining > 0) {
                const urgent = remaining < 3600; // أقل من ساعة = عاجل
                timerHtml = `<span class="history-timer ${urgent ? 'urgent' : ''}">⏰ ${formatRemaining(remaining)}</span>`;
            }
            
            const statusIcon = item.status === 'complete' ? '✅' : item.status === 'error' ? '❌' : '⏳';
            
            // تجهيز بيانات الوصف
            const surahName = item.surahName || t('surah');
            const reciterName = item.reciter || t('reciter');
            const ayahRange = item.startAyah && item.endAyah ? `(${item.startAyah}-${item.endAyah})` : '';
            
            let actionsHtml = '';
            if (item.downloadUrl && remaining > 0) {
                const trackedUrl = trackedDownloadUrl(item.downloadUrl, item.jobId);
                actionsHtml = `
                    <button onclick="previewVideo('${item.downloadUrl}')">${t('preview')}</button>
                    <a href="${trackedUrl}" download onclick="refreshMediaViewsLater()">${t('download')}</a>
                    <button onclick="openVideoEditor('${item.jobId}', false)">${CURRENT_LANG === 'ar' ? '✏️ تعديل' : '✏️ Edit'}</button>
                    <button onclick="openVideoEditor('${item.jobId}', true)">${CURRENT_LANG === 'ar' ? '♻️ إعادة إنشاء' : '♻️ Regenerate'}</button>
                    <button onclick="openYoutubeDialog('${item.jobId}', '${item.title?.replace(/'/g, "\\'") || t('generateVideoBtn').replace('✨ ', '')}', '${reciterName.replace(/'/g, "\\'")}', '${surahName}')" style="background: #ff0000; color: white; border: none;">${t('youtube')}</button>
                    <button class="btn-delete" onclick="deleteHistoryItem(${item.id})">🗑️</button>
                `;
            } else {
                actionsHtml = `
                    <span style="color: var(--text-muted); font-size: 0.85rem;">${t('unavailable')}</span>
                    <button onclick="openVideoEditor('${item.jobId}', false)">${CURRENT_LANG === 'ar' ? '✏️ تعديل' : '✏️ Edit'}</button>
                    <button onclick="openVideoEditor('${item.jobId}', true)">${CURRENT_LANG === 'ar' ? '♻️ إعادة إنشاء' : '♻️ Regenerate'}</button>
                    <button class="btn-delete" onclick="deleteHistoryItem(${item.id})">🗑️</button>
                `;
            }
            
            return `
                <div class="history-item" data-id="${item.id}">
                    <div class="history-item-header">
                        <span class="history-item-title">${item.title}</span>
                        <span class="history-item-status">${statusIcon}</span>
                    </div>
                    <div class="history-item-meta">
                        ${timerHtml}
                        🎤 ${item.reciter || t('unspecified')} • 📺 ${item.quality}p • 🕒 ${dateStr}
                    </div>
                    <div class="history-item-actions">
                        ${actionsHtml}
                    </div>
                </div>
            `;
        }

        function mediaStatusLabel(status) {
            const labels = CURRENT_LANG === 'ar'
                ? {
                    all: 'الكل',
                    undownloaded: 'غير مُنزّل',
                    downloaded: 'مُنزّل',
                    failed: 'فاشل',
                    expired: 'منتهي'
                }
                : {
                    all: 'All',
                    undownloaded: 'Undownloaded',
                    downloaded: 'Downloaded',
                    failed: 'Failed',
                    expired: 'Expired'
                };
            return labels[status] || status;
        }

        async function loadMediaHub(filter = mediaHubFilter) {
            mediaHubFilter = filter;
            try {
                const res = await fetch(`/api/media-hub?sessionId=${encodeURIComponent(SESSION_ID)}&filter=${encodeURIComponent(filter)}&limit=300`);
                const data = await res.json();

                const list = document.getElementById('mediaList');
                const empty = document.getElementById('mediaEmpty');
                if (!list || !empty) return;

                const items = (data && data.ok && Array.isArray(data.items)) ? data.items : [];
                if (items.length === 0) {
                    list.innerHTML = '';
                    empty.style.display = 'block';
                    return;
                }

                empty.style.display = 'none';
                list.innerHTML = items.map(createMediaCard).join('');
            } catch (err) {
                console.error('Media hub load error:', err);
            }
        }

        function setMediaFilter(filter, el) {
            document.querySelectorAll('#mediaFilters .media-filter-btn').forEach(btn => btn.classList.remove('active'));
            if (el) el.classList.add('active');
            loadMediaHub(filter);
        }

        function createMediaCard(item) {
            const dateValue = item.createdAt ? new Date(item.createdAt) : new Date();
            const dateStr = dateValue.toLocaleDateString(localeCode()) + ' ' + dateValue.toLocaleTimeString(localeCode(), { hour: '2-digit', minute: '2-digit' });
            const hasDownload = !!item.downloadUrl;
            const tracked = hasDownload ? trackedDownloadUrl(item.downloadUrl, item.jobId) : '#';
            const canDelete = typeof item.id === 'number' || (typeof item.id === 'string' && item.id.length > 0);

            return `
                <div class="media-card" data-id="${item.id}">
                    <div class="media-card-head">
                        <div class="media-title">${item.title || (CURRENT_LANG === 'ar' ? 'فيديو قرآني' : 'Quran Video')}</div>
                        <span class="media-badge">${mediaStatusLabel(item.mediaStatus)}</span>
                    </div>
                    <div class="media-meta">
                        🎤 ${item.reciter || t('unspecified')} • 📖 ${item.surah || '-'} (${item.startAyah || '-'}-${item.endAyah || '-'}) • 🕒 ${dateStr}
                        <br>
                        ⬇️ ${CURRENT_LANG === 'ar' ? 'عدد التنزيلات' : 'Downloads'}: ${item.downloadCount || 0}
                    </div>
                    <div class="media-actions">
                        <button ${hasDownload ? '' : 'disabled'} onclick="previewVideo('${item.downloadUrl || ''}')">${CURRENT_LANG === 'ar' ? '▶️ عرض' : '▶️ Preview'}</button>
                        <a ${hasDownload ? '' : 'style="pointer-events:none; opacity:.5;"'} href="${tracked}" download onclick="refreshMediaViewsLater()">${CURRENT_LANG === 'ar' ? '⬇️ تنزيل' : '⬇️ Download'}</a>
                        <button onclick="openVideoEditor('${item.jobId}', false)">${CURRENT_LANG === 'ar' ? '✏️ تعديل' : '✏️ Edit'}</button>
                        <button onclick="openVideoEditor('${item.jobId}', true)">${CURRENT_LANG === 'ar' ? '♻️ إعادة' : '♻️ Regenerate'}</button>
                        <button onclick="openYoutubeDialog('${item.jobId}', '${(item.title || '').replace(/'/g, "\\'")}', '${(item.reciter || '').replace(/'/g, "\\'")}', '${item.surah || ''}')">${CURRENT_LANG === 'ar' ? '📺 يوتيوب' : '📺 YouTube'}</button>
                        <button class="danger" ${canDelete ? '' : 'disabled'} onclick="${canDelete ? `deleteHistoryItem(${item.id})` : ''}">${CURRENT_LANG === 'ar' ? '🗑️ حذف' : '🗑️ Delete'}</button>
                    </div>
                </div>
            `;
        }

        // ═══════════════════════════════════════
        // 📺 YouTube Integration
        // ═══════════════════════════════════════
        let youtubeAuthWindow = null;
        let currentYoutubeJob = null;

        async function checkYoutubeStatus() {
            try {
                const res = await fetch(`/api/youtube/status?sessionId=${encodeURIComponent(SESSION_ID)}&lang=${encodeURIComponent(CURRENT_LANG)}`);
                return await res.json();
            } catch {
                return { configured: false, authorized: false };
            }
        }

        async function openYoutubeDialog(jobId, defaultTitle, reciterName, surahName) {
            currentYoutubeJob = jobId;
            
            // إعداد الوصف الافتراضي
            const defaultDescription = CURRENT_LANG === 'ar'
                ? `قرآن كريم بصوت القارئ ${reciterName || 'قارئ'} من سورة ${surahName || 'سورة'}\n\n#قران_كريم #قران #quran #fyp #قرآن_كريم_راحة_نفسية #قرآن_كريم`
                : `Quran recitation by ${reciterName || 'reciter'} from ${surahName || 'a surah'}\n\n#quran #recitation #islam #shorts`;
            
            // إعداد الكلمات المفتاحية
            const defaultTags = CURRENT_LANG === 'ar'
                ? 'قرآن كريم, تلاوة, إسلام, Quran, قرآن, تلاوة قرآنية'
                : 'quran, recitation, islam, islamic, shorts';
            
            // التحقق من حالة YouTube
            const status = await checkYoutubeStatus();
            
            if (!status.configured) {
                showToast(t('youtubeNotConfigured'), 'error');
                return;
            }
            
            if (!status.authorized) {
                // عرض الـ redirect URI للمستخدم
                if (status.redirectUri) {
                    console.log('YouTube Redirect URI:', status.redirectUri);
                }
                
                // فتح نافذة المصادقة
                const authRes = await fetch(`/api/youtube/auth-url?sessionId=${encodeURIComponent(SESSION_ID)}&lang=${encodeURIComponent(CURRENT_LANG)}`);
                const authData = await authRes.json();
                
                if (authData.authUrl) {
                    showToast(t('youtubeAuthOpening'), 'success');
                    youtubeAuthWindow = window.open(authData.authUrl, 'youtube-auth', 'width=500,height=600');
                    
                    // الاستماع لرسالة النجاح
                    window.addEventListener('message', function ytAuthHandler(e) {
                        if (e.data.type === 'youtube_auth_success') {
                            showToast(t('youtubeLinked'), 'success');
                            window.removeEventListener('message', ytAuthHandler);
                            // فتح الـ dialog مرة أخرى
                            setTimeout(() => openYoutubeDialog(jobId, defaultTitle), 500);
                        }
                    });
                    
                    // التحقق من إغلاق النافذة (في حالة الخطأ)
                    const checkClosed = setInterval(() => {
                        if (youtubeAuthWindow && youtubeAuthWindow.closed) {
                            clearInterval(checkClosed);
                            // التحقق من الحالة مرة أخرى بعد إغلاق النافذة
                            setTimeout(async () => {
                                const newStatus = await checkYoutubeStatus();
                                if (!newStatus.authorized && newStatus.redirectUri) {
                                    // عرض رسالة مساعدة للمستخدم
                                    showToast(t('youtubeRedirectHint'), 'error', 8000);
                                    console.log('أضف هذا URL في Google Cloud Console:', newStatus.redirectUri);
                                }
                            }, 1000);
                        }
                    }, 500);
                }
                return;
            }
            
            // عرض Dialog النشر
            showYoutubeUploadDialog(jobId, defaultTitle, defaultDescription, defaultTags);
        }

        function showYoutubeUploadDialog(jobId, defaultTitle, defaultDescription, defaultTags) {
            // إنشاء الـ dialog
            // حساب أقرب وقت للجدولة (بعد ساعة من الآن)
            const now = new Date();
            now.setHours(now.getHours() + 1);
            const minScheduleTime = now.toISOString().slice(0, 16);
            
            const dialog = document.createElement('div');
            dialog.id = 'youtubeDialog';
            dialog.innerHTML = `
                <div style="position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 9999; display: flex; align-items: center; justify-content: center;">
                    <div style="background: var(--bg-card); border-radius: 16px; padding: 24px; width: 90%; max-width: 450px; max-height: 90vh; overflow-y: auto;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                            <h3 style="color: #ff0000;">${t('youtubeDialogTitle')}</h3>
                            <button onclick="closeYoutubeDialog()" style="background: none; border: none; color: var(--text-muted); font-size: 1.5rem; cursor: pointer;">✕</button>
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">${t('ytTitleLabel')}</label>
                            <input type="text" id="ytTitle" class="form-input" value="${defaultTitle}" maxlength="100" placeholder="${t('ytTitlePlaceholder')}">
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">${t('ytDescriptionLabel')}</label>
                            <textarea id="ytDescription" class="form-input" style="height: 100px; resize: vertical;" placeholder="${t('ytDescriptionPlaceholder')}">${defaultDescription || ''}</textarea>
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">${t('ytTagsLabel')}</label>
                            <input type="text" id="ytTags" class="form-input" value="${defaultTags}" placeholder="${t('ytTagsPlaceholder')}">
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">${t('ytPrivacyLabel')}</label>
                            <select id="ytPrivacy" class="form-select" onchange="toggleScheduleOption()">
                                <option value="unlisted">${t('ytPrivacyUnlisted')}</option>
                                <option value="private">${t('ytPrivacyPrivate')}</option>
                                <option value="public">${t('ytPrivacyPublic')}</option>
                                <option value="scheduled">${t('ytPrivacyScheduled')}</option>
                            </select>
                        </div>
                        
                        <div id="scheduleOptions" style="display: none; margin-top: 12px; padding: 16px; background: var(--bg-input); border-radius: 8px;">
                            <label class="form-label" style="margin-bottom: 8px;">${t('ytScheduleLabel')}</label>
                            <input type="datetime-local" id="ytScheduleTime" class="form-input" min="${minScheduleTime}" style="width: 100%;">
                            <p style="font-size: 12px; color: var(--text-muted); margin-top: 8px;">
                                ${t('ytScheduleNote')}
                            </p>
                        </div>
                        
                        <div style="margin-top: 20px; display: flex; gap: 10px;">
                            <button onclick="uploadToYoutube('${jobId}')" class="btn-primary" style="flex: 1;">
                                <span id="uploadBtnText">${t('ytPublishNow')}</span>
                            </button>
                            <button onclick="closeYoutubeDialog()" class="btn-secondary" style="flex: 1;">
                                ${t('ytCancel')}
                            </button>
                        </div>
                        
                        <div id="youtubeUploadProgress" style="display: none; margin-top: 16px; text-align: center;">
                            <div style="color: var(--accent);">${t('ytUploading')}</div>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(dialog);
        }
        
        function toggleScheduleOption() {
            const privacy = document.getElementById('ytPrivacy')?.value;
            const scheduleOptions = document.getElementById('scheduleOptions');
            const uploadBtnText = document.getElementById('uploadBtnText');
            
            if (privacy === 'scheduled') {
                scheduleOptions.style.display = 'block';
                uploadBtnText.textContent = t('ytSchedulePublish');
            } else {
                scheduleOptions.style.display = 'none';
                uploadBtnText.textContent = t('ytPublishNow');
            }
        }

        function closeYoutubeDialog() {
            const dialog = document.getElementById('youtubeDialog');
            if (dialog) dialog.remove();
        }

        async function uploadToYoutube(jobId) {
            const title = document.getElementById('ytTitle')?.value || t('generateVideoBtn').replace('✨ ', '');
            const description = document.getElementById('ytDescription')?.value || '';
            const tags = document.getElementById('ytTags')?.value.split(',').map(t => t.trim()).filter(t => t) || [];
            let privacyStatus = document.getElementById('ytPrivacy')?.value || 'unlisted';
            const scheduleTimeLocal = document.getElementById('ytScheduleTime')?.value || null;
            
            // التحقق من وقت الجدولة
            let scheduleTime = null;
            if (privacyStatus === 'scheduled') {
                if (!scheduleTimeLocal) {
                    showToast(t('schedulePickTime'), 'error');
                    return;
                }
                // تحويل الوقت المحلي لـ ISO string مع timezone
                const scheduledDate = new Date(scheduleTimeLocal);
                const now = new Date();
                const diffMinutes = (scheduledDate - now) / (1000 * 60);
                if (diffMinutes < 15) {
                    showToast(t('scheduleMin15'), 'error');
                    return;
                }
                // تحويل لـ ISO string (يتضمن timezone)
                scheduleTime = scheduledDate.toISOString();
                console.log('[YouTube] Local time:', scheduleTimeLocal);
                console.log('[YouTube] UTC time:', scheduleTime);
                // للجدولة، نرفع الفيديو كـ scheduled
                privacyStatus = 'scheduled';
            }
            
            const progressEl = document.getElementById('youtubeUploadProgress');
            if (progressEl) progressEl.style.display = 'block';
            
            try {
                const res = await fetch('/api/youtube/upload', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        sessionId: SESSION_ID,
                        lang: CURRENT_LANG,
                        jobId: jobId,
                        title: title,
                        description: description,
                        tags: tags,
                        privacyStatus: privacyStatus,
                        scheduleTime: scheduleTime
                    })
                });
                
                const data = await res.json();
                
                if (data.ok) {
                    closeYoutubeDialog();
                    if (privacyStatus === 'scheduled') {
                        showToast(t('scheduledSuccess'), 'success');
                    } else {
                        showToast(t('publishedSuccess'), 'success');
                    }
                    
                    // عرض رابط الفيديو
                    if (data.videoUrl) {
                        setTimeout(() => {
                            const message = privacyStatus === 'scheduled' 
                                ? t('scheduledConfirm', { time: new Date(scheduleTime).toLocaleString(localeCode()), url: data.videoUrl })
                                : t('publishedConfirm', { url: data.videoUrl });
                            if (confirm(message)) {
                                window.open(data.videoUrl, '_blank');
                            }
                        }, 500);
                    }
                } else {
                    if (data.needsAuth) {
                        showToast(t('youtubeMustConnect'), 'error');
                        closeYoutubeDialog();
                        // إعادة المصادقة
                        openYoutubeDialog(jobId, title);
                    } else {
                        showToast(`❌ ${data.error || t('uploadFailed')}`, 'error');
                    }
                }
            } catch (err) {
                console.error('YouTube upload error:', err);
                showToast(t('connectionFailed'), 'error');
            }
            
            if (progressEl) progressEl.style.display = 'none';
        }

        async function deleteHistoryItem(id) {
            if (!confirm(t('deleteItemConfirm'))) return;
            
            try {
                const res = await fetch(`/api/history/${id}?sessionId=${encodeURIComponent(SESSION_ID)}`, { method: 'DELETE' });
                const data = await res.json();
                
                if (data.ok) {
                    document.querySelector(`.history-item[data-id="${id}"]`)?.remove();
                    if (document.querySelectorAll('.history-item').length === 0) {
                        document.getElementById('historyEmpty').style.display = 'block';
                    }
                    loadMediaHub(mediaHubFilter);
                    showToast(t('deleted'), 'success');
                }
            } catch (err) {
                showToast(t('deleteFailed'), 'error');
            }
        }

        async function clearAllHistory() {
            if (!confirm(t('clearHistoryConfirm'))) return;
            
            try {
                const res = await fetch('/api/history/clear', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ sessionId: SESSION_ID })
                });
                const data = await res.json();
                
                if (data.ok) {
                    document.getElementById('historyList').innerHTML = '';
                    document.getElementById('historyEmpty').style.display = 'block';
                    loadMediaHub(mediaHubFilter);
                    showToast(t('historyCleared'), 'success');
                }
            } catch (err) {
                showToast(t('historyClearFailed'), 'error');
            }
        }

        async function previewVideo(url) {
            try {
                document.querySelector('[data-tab="main"]').click();
                showProgress();
                document.getElementById('progressStatus').textContent = t('loadingVideo');
                
                const res = await fetch(sessionScopedUrl(url));
                const blob = await res.blob();
                const blobUrl = URL.createObjectURL(blob);
                
                document.getElementById('progressSection').classList.remove('active');
                document.getElementById('resultSection').classList.add('active');
                document.getElementById('videoPlayer').src = blobUrl;
                const downloadLinkEl = document.getElementById('downloadLink');
                downloadLinkEl.href = trackedDownloadUrl(url);
                downloadLinkEl.onclick = () => { refreshMediaViewsLater(); };
                refreshStorageInfo();
            } catch (err) {
                showToast(t('loadingVideoFailed'), 'error');
                resetForm();
            }
        }

        // ═══════════════════════════════════════
        // ⚙️ Settings
        // ═══════════════════════════════════════
        function getStyleSettings() {
            return {
                arColor: document.getElementById('arColor')?.value || '#ffffff',
                arHighlightColor: document.getElementById('arHighlightColor')?.value || '#ffd700',
                arSize: document.getElementById('arSize')?.value || '1',
                arOutC: document.getElementById('arOutlineColor')?.value || '#000000',
                arOutW: document.getElementById('arOutlineWidth')?.value || '4',
                enColor: document.getElementById('enColor')?.value || '#FFD700',
                enSize: document.getElementById('enSize')?.value || '1',
                enOutC: document.getElementById('enOutlineColor')?.value || '#000000',
                enOutW: document.getElementById('enOutlineWidth')?.value || '3'
            };
        }

        function loadSettings() {
            const saved = JSON.parse(localStorage.getItem('quran_app_styles_v2')) || defaultSettings;
            
            Object.entries(saved).forEach(([key, value]) => {
                const el = document.getElementById(key);
                if (el) el.value = value;
            });
            
            const pexelsKey = localStorage.getItem('user_pexels_key');
            if (pexelsKey) {
                document.getElementById('pexelsKey').value = pexelsKey;
            }
            
            updatePexelsBanner();
            updatePreview();
            initPresets();
        }

        function updatePexelsBanner() {
            const banner = document.getElementById('pexelsBanner');
            if (!banner) return;
            const hasKey = !!(localStorage.getItem('user_pexels_key') || '').trim();
            const dismissed = sessionStorage.getItem('pexels_banner_dismissed') === '1';
            // Also check backend env via /api/config (best-effort) — if server has a key, hide
            const serverHas = window.__serverHasPexels === true;
            banner.style.display = (hasKey || serverHas || dismissed) ? 'none' : 'block';
        }

        document.addEventListener('DOMContentLoaded', () => {
            const saveBtn = document.getElementById('bannerSaveBtn');
            const dismissBtn = document.getElementById('bannerDismissBtn');
            const input = document.getElementById('bannerPexelsInput');
            if (saveBtn && input) {
                saveBtn.addEventListener('click', () => {
                    const v = (input.value || '').trim();
                    if (v.length < 10) { alert('المفتاح يبدو قصيراً جداً'); return; }
                    localStorage.setItem('user_pexels_key', v);
                    const settingsField = document.getElementById('pexelsKey');
                    if (settingsField) settingsField.value = v;
                    updatePexelsBanner();
                });
            }
            if (dismissBtn) {
                dismissBtn.addEventListener('click', () => {
                    sessionStorage.setItem('pexels_banner_dismissed', '1');
                    updatePexelsBanner();
                });
            }
            // Probe server config to see if PEXELS_API_KEYS is set server-side
            fetch('/api/config').then(r => r.json()).then(cfg => {
                window.__serverHasPexels = !!(cfg && cfg.has_pexels_key);
                updatePexelsBanner();
            }).catch(() => {});
        });

        function updatePreview() {
            const ar = document.getElementById('previewAr');
            const en = document.getElementById('previewEn');
            const guideTop = document.getElementById('safeGuideTop');
            const guideBottom = document.getElementById('safeGuideBottom');
            const showGuides = document.getElementById('safeAreaGuides')?.checked;
            const padPx = parseInt(document.getElementById('safeAreaPaddingPx')?.value || '48');
            
            ar.style.color = document.getElementById('arColor').value;
            ar.style.fontSize = `${1.5 * parseFloat(document.getElementById('arSize').value)}rem`;
            const arOutline = parseInt(document.getElementById('arOutlineWidth').value) / 5;
            ar.style.webkitTextStroke = arOutline > 0 ? `${arOutline}px ${document.getElementById('arOutlineColor').value}` : 'none';
            
            // Dynamic translation text based on selected translationLang
            const transLang = document.getElementById('translationLang')?.value || 'en';
            const previews = {
                'en': 'In the name of Allah, the Entirely Merciful',
                'ur': 'شروع اللہ کے نام سے جو بڑا مہربان نہایت رحم والا ہے',
                'fr': "Au nom d'Allah, le Tout Miséricordieux, le Très Miséricordieux",
                'es': 'En el nombre de Alá, el Compasivo, el Misericordioso',
                'id': 'Dengan menyebut nama Allah Yang Maha Pengasih lagi Maha Penyayang'
            };
            if (en) {
                en.textContent = previews[transLang] || previews['en'];
                en.style.color = document.getElementById('enColor').value;
                en.style.fontSize = `${0.85 * parseFloat(document.getElementById('enSize').value)}rem`;
                const enOutline = parseInt(document.getElementById('enOutlineWidth').value) / 5;
                en.style.webkitTextStroke = enOutline > 0 ? `${enOutline}px ${document.getElementById('enOutlineColor').value}` : 'none';
            }

            if (guideTop && guideBottom) {
                const topPercent = Math.max(4, Math.min(25, (padPx / 320) * 100));
                guideTop.style.top = `${topPercent}%`;
                guideBottom.style.bottom = `${topPercent}%`;
                guideTop.style.display = showGuides ? 'block' : 'none';
                guideBottom.style.display = showGuides ? 'block' : 'none';
            }
        }

        function saveAllSettings() {
            const settings = {};
            ['arColor', 'arHighlightColor', 'arSize', 'arOutlineColor', 'arOutlineWidth', 
             'enColor', 'enSize', 'enOutlineColor', 'enOutlineWidth'].forEach(key => {
                const el = document.getElementById(key);
                if (el) settings[key] = el.value;
            });
            
            localStorage.setItem('quran_app_styles_v2', JSON.stringify(settings));
            
            const pexelsKey = document.getElementById('pexelsKey').value;
            if (pexelsKey) {
                localStorage.setItem('user_pexels_key', pexelsKey);
            } else {
                localStorage.removeItem('user_pexels_key');
            }
            
            showToast(t('settingsSaved'), 'success');
        }

        function resetAllSettings() {
            if (!confirm(t('resetSettingsConfirm'))) return;
            
            localStorage.removeItem('quran_app_styles_v2');
            localStorage.removeItem('user_pexels_key');
            document.getElementById('pexelsKey').value = '';
            loadSettings();
            showToast(t('settingsRestored'), 'success');
        }

        const BUILTIN_PRESETS = {
            'default': {
                name: 'الافتراضي / Default White',
                arColor: '#ffffff',
                arHighlightColor: '#ffd700',
                arSize: '1.0',
                arOutlineColor: '#000000',
                arOutlineWidth: '4',
                enColor: '#FFD700',
                enSize: '1.0',
                enOutlineColor: '#000000',
                enOutlineWidth: '3'
            },
            'emerald': {
                name: 'أخضر زمردي / Emerald Green',
                arColor: '#e6fffa',
                arHighlightColor: '#ffd700',
                arSize: '1.1',
                arOutlineColor: '#0f5132',
                arOutlineWidth: '5',
                enColor: '#ffd700',
                enSize: '1.0',
                enOutlineColor: '#0f5132',
                enOutlineWidth: '3'
            },
            'royal_gold': {
                name: 'ذهبي ملكي / Royal Gold',
                arColor: '#ffd700',
                arHighlightColor: '#ffffff',
                arSize: '1.1',
                arOutlineColor: '#1a0f00',
                arOutlineWidth: '5',
                enColor: '#ffffff',
                enSize: '0.9',
                enOutlineColor: '#1a0f00',
                enOutlineWidth: '3'
            },
            'neon_cyan': {
                name: 'نيون / Cyber Neon',
                arColor: '#00ffff',
                arHighlightColor: '#ffff00',
                arSize: '1.0',
                arOutlineColor: '#000000',
                arOutlineWidth: '4',
                enColor: '#ff00ff',
                enSize: '1.0',
                enOutlineColor: '#000000',
                enOutlineWidth: '3'
            },
            'rose_gold': {
                name: 'وردي ذهبي / Rose Gold',
                arColor: '#ffe3e3',
                arHighlightColor: '#ffd700',
                arSize: '1.0',
                arOutlineColor: '#2b0000',
                arOutlineWidth: '4',
                enColor: '#ffd700',
                enSize: '1.0',
                enOutlineColor: '#2b0000',
                enOutlineWidth: '3'
            }
        };

        function getCustomPresets() {
            try {
                return JSON.parse(localStorage.getItem('quran_custom_presets')) || {};
            } catch (e) {
                return {};
            }
        }

        function saveCustomPresets(presets) {
            localStorage.setItem('quran_custom_presets', JSON.stringify(presets));
        }

        function initPresets() {
            const select = document.getElementById('presetSelect');
            if (!select) return;

            // Clear previous options except first
            select.innerHTML = '<option value="">-- اختر قالب / Select Preset --</option>';

            // Populate Built-in
            Object.entries(BUILTIN_PRESETS).forEach(([key, preset]) => {
                const opt = document.createElement('option');
                opt.value = 'builtin_' + key;
                opt.textContent = preset.name;
                select.appendChild(opt);
            });

            // Populate Custom
            const custom = getCustomPresets();
            Object.entries(custom).forEach(([key, preset]) => {
                const opt = document.createElement('option');
                opt.value = 'custom_' + key;
                opt.textContent = `⭐ ${key}`;
                select.appendChild(opt);
            });

            renderCustomPresetsList();
        }

        function renderCustomPresetsList() {
            const container = document.getElementById('customPresetsList');
            if (!container) return;

            container.innerHTML = '';
            const custom = getCustomPresets();

            Object.keys(custom).forEach(key => {
                const tag = document.createElement('div');
                tag.style.cssText = 'display: flex; align-items: center; gap: 8px; background: var(--bg-input); border: 1px solid var(--border); padding: 4px 10px; border-radius: 20px; font-size: 0.8rem;';
                tag.innerHTML = `
                    <span style="cursor: pointer;" onclick="applyPreset('custom_${key}')">⭐ ${key}</span>
                    <span style="color: var(--danger); cursor: pointer; font-weight: bold;" onclick="deleteCustomPreset('${key}')">×</span>
                `;
                container.appendChild(tag);
            });
        }

        function applyPreset(presetVal) {
            if (!presetVal) return;

            let preset = null;
            if (presetVal.startsWith('builtin_')) {
                const key = presetVal.replace('builtin_', '');
                preset = BUILTIN_PRESETS[key];
            } else if (presetVal.startsWith('custom_')) {
                const key = presetVal.replace('custom_', '');
                preset = getCustomPresets()[key];
            }

            if (!preset) return;

            // Apply style settings to DOM inputs
            Object.entries(preset).forEach(([key, value]) => {
                if (key === 'name') return;
                const el = document.getElementById(key);
                if (el) el.value = value;
            });

            updatePreview();
            saveAllSettings();
            showToast(t('presetApplied') || 'تم تطبيق القالب بنجاح', 'success');
        }

        function saveCustomPreset() {
            const nameEl = document.getElementById('customPresetName');
            if (!nameEl) return;

            const name = nameEl.value.trim();
            if (!name) {
                showToast(t('enterPresetName') || 'الرجاء إدخال اسم القالب', 'error');
                return;
            }

            const currentStyle = getStyleSettings();
            const preset = {
                arColor: currentStyle.arColor,
                arHighlightColor: currentStyle.arHighlightColor,
                arSize: currentStyle.arSize,
                arOutlineColor: currentStyle.arOutC,
                arOutlineWidth: currentStyle.arOutW,
                enColor: currentStyle.enColor,
                enSize: currentStyle.enSize,
                enOutlineColor: currentStyle.enOutC,
                enOutlineWidth: currentStyle.enOutW
            };

            const custom = getCustomPresets();
            custom[name] = preset;
            saveCustomPresets(custom);

            nameEl.value = '';
            initPresets();
            showToast(t('presetSaved') || 'تم حفظ القالب المخصص', 'success');
        }

        function deleteCustomPreset(name) {
            if (!confirm((t('deletePresetConfirm') || 'هل تريد حذف القالب المخصص: ') + name + '?')) return;

            const custom = getCustomPresets();
            delete custom[name];
            saveCustomPresets(custom);

            initPresets();
            showToast(t('presetDeleted') || 'تم حذف القالب', 'success');
        }

        // ═══════════════════════════════════════
        // 🎨 Theme
        // ═══════════════════════════════════════
        function toggleTheme() {
            document.body.classList.toggle('light-theme');
            const isLight = document.body.classList.contains('light-theme');
            document.getElementById('themeBtn').textContent = isLight ? '☀️' : '🌙';
            localStorage.setItem('theme', isLight ? 'light' : 'dark');
        }

        if (localStorage.getItem('theme') === 'light') {
            document.body.classList.add('light-theme');
            document.getElementById('themeBtn').textContent = '☀️';
        }

        // ═══════════════════════════════════════
        // 🔔 Toast Notifications
        // ═══════════════════════════════════════
        function showToast(message, type = 'success') {
            const container = document.getElementById('toastContainer');
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.textContent = message;
            container.appendChild(toast);
            
            setTimeout(() => toast.remove(), 3000);
        }

        // ═══════════════════════════════════════
        // 🔄 Check Running Job
        // ═══════════════════════════════════════
        async function checkRunningJob() {
            try {
                const res = await fetch(`/api/my-jobs?status=processing&sessionId=${encodeURIComponent(SESSION_ID)}`);
                const data = await res.json();
                
                if (data.ok && data.jobs && data.jobs.length > 0) {
                    const job = data.jobs[0];
                    
                    const action = confirm(t('runningJobResume', { percent: job.percent }));
                    
                    if (action) {
                        currentJobId = job.id;
                        showProgress();
                        startPolling(job.id);
                    }
                }
            } catch (err) {
                console.log('No running jobs');
            }
        }

        // ═══════════════════════════════════════
        // 📦 Batch System
        // ═══════════════════════════════════════
        let batchItems = [];
        let currentBatchId = null;
        let batchCancelled = false;
        let selectedRecitersForRandom = []; // القراء المحددين للعشوائي

        // 🎤 إدارة قراء العشوائي
        function toggleReciterFilter() {
            const section = document.getElementById('reciterFilterSection');
            const toggle = document.getElementById('reciterFilterToggle');
            if (section.style.display === 'none') {
                section.style.display = 'block';
                toggle.style.transform = 'rotate(180deg)';
            } else {
                section.style.display = 'none';
                toggle.style.transform = 'rotate(0deg)';
            }
        }

        function initReciterCheckboxes() {
            const container = document.getElementById('reciterCheckboxes');
            const reciterSelect = document.getElementById('batchReciterSelect');
            if (!container || !reciterSelect) return;

            container.innerHTML = '';
            
            // تحميل الاختيارات المحفوظة
            const saved = localStorage.getItem('selectedRecitersForRandom');
            if (saved) {
                try {
                    selectedRecitersForRandom = JSON.parse(saved);
                } catch (e) {
                    selectedRecitersForRandom = [];
                }
            }

            // إنشاء checkboxes
            for (let i = 0; i < reciterSelect.options.length; i++) {
                const option = reciterSelect.options[i];
                const reciterValue = option.value;
                const reciterName = option.text;
                
                // لو مفيش محفوظات، نحدد الكل افتراضياً
                const isChecked = selectedRecitersForRandom.length === 0 || selectedRecitersForRandom.includes(reciterValue);
                
                const label = document.createElement('label');
                label.style.cssText = 'display: flex; align-items: center; gap: 8px; cursor: pointer; padding: 4px 8px; border-radius: 4px; transition: background 0.2s;';
                label.innerHTML = `
                    <input type="checkbox" value="${reciterValue}" ${isChecked ? 'checked' : ''} onchange="updateSelectedReciters()" style="width: 16px; height: 16px; cursor: pointer;">
                    <span style="font-size: 0.85rem;">${reciterName}</span>
                `;
                label.onmouseenter = () => label.style.background = 'var(--bg-card)';
                label.onmouseleave = () => label.style.background = 'transparent';
                container.appendChild(label);
            }

            // تحديث القائمة المحددة
            updateSelectedReciters();
        }

        function updateSelectedReciters() {
            const checkboxes = document.querySelectorAll('#reciterCheckboxes input[type="checkbox"]');
            selectedRecitersForRandom = [];
            checkboxes.forEach(cb => {
                if (cb.checked) {
                    selectedRecitersForRandom.push(cb.value);
                }
            });
            
            // حفظ في localStorage
            localStorage.setItem('selectedRecitersForRandom', JSON.stringify(selectedRecitersForRandom));
        }

        function selectAllReciters() {
            const checkboxes = document.querySelectorAll('#reciterCheckboxes input[type="checkbox"]');
            checkboxes.forEach(cb => cb.checked = true);
            updateSelectedReciters();
        }

        function deselectAllReciters() {
            const checkboxes = document.querySelectorAll('#reciterCheckboxes input[type="checkbox"]');
            checkboxes.forEach(cb => cb.checked = false);
            updateSelectedReciters();
            // لازم على الأقل قارئ واحد يكون محدد
            if (checkboxes.length > 0) {
                checkboxes[0].checked = true;
                updateSelectedReciters();
            }
        }

        function randomizeBatch() {
            const reciterSelect = document.getElementById('batchReciterSelect');
            const surahSelect = document.getElementById('batchSurahSelect');
            
            // 🎯 اختيار قارئ عشوائي من المحددين فقط
            if (selectedRecitersForRandom.length > 0) {
                const randomReciter = selectedRecitersForRandom[Math.floor(Math.random() * selectedRecitersForRandom.length)];
                // البحث عن الـ index في الـ select
                for (let i = 0; i < reciterSelect.options.length; i++) {
                    if (reciterSelect.options[i].value === randomReciter) {
                        reciterSelect.selectedIndex = i;
                        break;
                    }
                }
            } else if (reciterSelect.options.length > 0) {
                reciterSelect.selectedIndex = Math.floor(Math.random() * reciterSelect.options.length);
            }
            
            if (surahSelect.options.length > 0) {
                surahSelect.selectedIndex = Math.floor(Math.random() * surahSelect.options.length);
                const max = VERSE_COUNTS[parseInt(surahSelect.value)] || 286;
                const start = Math.floor(Math.random() * Math.max(1, max - 5)) + 1;
                document.getElementById('batchStartAyah').value = start;
                document.getElementById('batchEndAyah').value = Math.min(start + 4, max);
            }
            updateBatchEstimatedTime();
        }

        function adjustBatchAyah(id, delta) {
            const input = document.getElementById(id);
            const surah = parseInt(document.getElementById('batchSurahSelect').value);
            const max = VERSE_COUNTS[surah] || 286;
            let val = parseInt(input.value) + delta;
            
            if (val < 1) val = 1;
            if (val > max) val = max;
            input.value = val;
            
            const start = parseInt(document.getElementById('batchStartAyah').value);
            const end = parseInt(document.getElementById('batchEndAyah').value);
            if (id === 'batchStartAyah' && start > end) {
                document.getElementById('batchEndAyah').value = start;
            }
            if (id === 'batchEndAyah' && end < start) {
                document.getElementById('batchStartAyah').value = end;
            }
            
            updateBatchEstimatedTime();
        }

        const MAX_BATCH_VIDEOS = 10; // الحد الأقصى لعدد الفيديوهات في الدفعة

        function addToBatchList() {
            const reciterSelect = document.getElementById('batchReciterSelect');
            const surahSelect = document.getElementById('batchSurahSelect');
            
            // التحقق من الحد الأقصى
            if (batchItems.length >= MAX_BATCH_VIDEOS) {
                showToast(t('maxBatchLimit', { max: MAX_BATCH_VIDEOS }), 'error');
                return;
            }
            
            const reciter = reciterSelect.value;
            const reciterName = reciterSelect.options[reciterSelect.selectedIndex]?.text || t('unspecified');
            const surah = parseInt(surahSelect.value);
            const surahName = surahSelect.options[surahSelect.selectedIndex]?.text.replace(/^\d+\.\s*/, '') || t('unspecified');
            const startAyah = parseInt(document.getElementById('batchStartAyah').value);
            const endAyah = parseInt(document.getElementById('batchEndAyah').value);
            
            const exists = batchItems.some(item => 
                item.reciter === reciter && item.surah === surah && 
                item.startAyah === startAyah && item.endAyah === endAyah
            );
            
            if (exists) {
                showToast(t('alreadyInBatch'), 'error');
                return;
            }
            
            const effects = {
                dynamicBg: document.getElementById('batchDynamicBg').checked,
                useGlow: document.getElementById('batchUseGlow').checked,
                useVignette: document.getElementById('batchUseVignette').checked,
                backgroundEffect: document.getElementById('batchBackgroundEffect')?.value || 'enhance'
            };

            // ✅ إعدادات الفيديو الكاملة
            const videoSettings = {
                fps: parseInt(document.getElementById('batchFpsSelect')?.value || 20),
                quality: document.getElementById('batchQualitySelect')?.value || '720',
                aspectRatio: document.getElementById('batchAspectRatio')?.value || '9:16',
                font: document.getElementById('batchFontSelect')?.value || 'Arabic',
                fontEn: document.getElementById('batchFontEnSelect')?.value || 'English',
                translationLang: document.getElementById('batchTranslationLang')?.value || 'en',
                wordHighlight: document.getElementById('batchWordHighlight')?.checked ?? false,
                bgQuery: document.getElementById('batchUseSearch')?.checked ? (document.getElementById('batchBgQuery')?.value || '') : '',
                backgroundEffect: document.getElementById('batchBackgroundEffect')?.value || 'enhance',
                scenePack: document.getElementById('scenePack')?.value || 'nature_calm',
                bgCrossfadeSec: parseFloat(document.getElementById('bgCrossfadeSec')?.value || '0.5'),
                adaptiveTextContrast: document.getElementById('adaptiveTextContrast')?.checked ?? true,
                safeAreaGuides: document.getElementById('safeAreaGuides')?.checked ?? false,
                safeAreaPaddingPx: parseInt(document.getElementById('safeAreaPaddingPx')?.value || '48'),
                audioProfile: document.getElementById('audioProfile')?.value || 'studio',
                audioDenoise: document.getElementById('audioDenoise')?.checked ?? false,
                audioDeEss: document.getElementById('audioDeEss')?.checked ?? false
            };

            batchItems.push({
                reciter,
                reciterName,
                surah,
                startAyah,
                endAyah,
                surahName,
                effects,
                ...videoSettings
            });
            
            renderBatchList();
            showToast(t('addedToBatch', { surah: surahName, reciter: reciterName }), 'success');
        }

        function removeFromBatchList(index) {
            batchItems.splice(index, 1);
            renderBatchList();
            updateBatchTotalVideos();
        }

        function clearBatchList() {
            batchItems = [];
            renderBatchList();
            updateBatchTotalVideos();
            updateBatchTotalTime();
        }

        function updateBatchTotalVideos() {
            const totalVideosEl = document.getElementById('batchTotalVideos');
            if (totalVideosEl) totalVideosEl.textContent = batchItems.length;
            updateBatchTotalTime();
        }

        function renderBatchList() {
            const listEl = document.getElementById('batchList');
            const countEl = document.getElementById('batchCount');
            if (!listEl || !countEl) return;
            
            countEl.textContent = batchItems.length;
            updateBatchTotalVideos();
            updateBatchTotalTime();
            
            // لو القائمة فاضية
            if (batchItems.length === 0) {
                listEl.innerHTML = `
                    <div class="history-empty" id="batchListEmpty">
                        <p style="font-size: 0.85rem;">${t('batchEmpty')}</p>
                    </div>
                `;
                return;
            }
            
            // عرض الفيديوهات
            listEl.innerHTML = batchItems.map((item, index) => {
                const effectsIcons = [];
                if (item.effects.dynamicBg) effectsIcons.push('🖼️');
                if (item.effects.useGlow) effectsIcons.push('✨');
                if (item.effects.useVignette) effectsIcons.push('🎭');
                
                // محاولة الحصول على الوقت من الـ cache
                const cacheKey = `${item.reciter}-${item.surah}-${item.startAyah}-${item.endAyah}`;
                const cachedData = durationCache[cacheKey];
                const timeStr = cachedData ? localizeDurationText(cachedData.formatted) : '⏳...';
                
                return `
                <div class="batch-item" data-index="${index}" style="
                    background: var(--bg-card);
                    border: 1px solid var(--border);
                    border-radius: 10px;
                    padding: 12px;
                    margin-bottom: 8px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                ">
                    <div style="flex: 1;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div style="font-weight: 600; font-size: 0.95rem;">
                                📖 ${item.surahName}
                            </div>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span class="batch-item-time" data-index="${index}" style="font-size: 0.75rem; color: var(--accent);">⏱️ ${timeStr}</span>
                                <span style="font-size: 0.75rem; color: var(--text-muted);">#${index + 1}</span>
                            </div>
                        </div>
                        <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 4px;">
                            🎤 ${item.reciterName} • ${t('ayahWord')} ${item.startAyah} ← ${item.endAyah}
                        </div>
                        <div style="font-size: 0.75rem; color: var(--accent); margin-top: 4px;">
                            ${effectsIcons.join(' ')}
                        </div>
                    </div>
                    <button onclick="removeFromBatchList(${index})" style="
                        background: none;
                        border: none;
                        color: var(--danger);
                        font-size: 1.2rem;
                        cursor: pointer;
                        padding: 8px;
                    ">✕</button>
                </div>
            `}).join('');
            
            // تحديث أوقات الفيديوهات في الخلفية
            updateBatchItemTimes();
        }
        
        async function updateBatchItemTimes() {
            // تحديث وقت كل فيديو في القائمة
            for (let i = 0; i < batchItems.length; i++) {
                const item = batchItems[i];
                const data = await fetchEstimatedTime(item.reciter, item.surah, item.startAyah, item.endAyah);
                
                if (data && data.formatted) {
                    const timeEl = document.querySelector(`.batch-item-time[data-index="${i}"]`);
                    if (timeEl) {
                        timeEl.textContent = `⏱️ ${localizeDurationText(data.formatted)}`;
                    }
                }
            }
        }

        async function startBatchGeneration() {
            if (batchItems.length === 0) {
                showToast(t('addBatchFirst'), 'error');
                return;
            }
            
            batchCancelled = false;
            
            const payload = {
                sessionId: SESSION_ID,
                lang: CURRENT_LANG,
                items: batchItems.map(item => ({
                    surah: item.surah,
                    startAyah: item.startAyah,
                    endAyah: item.endAyah,
                    reciter: item.reciter,
                    dynamicBg: item.effects?.dynamicBg ?? true,
                    useGlow: item.effects?.useGlow ?? true,
                    useVignette: item.effects?.useVignette ?? true,
                    aspectRatio: item.aspectRatio || '9:16',
                    font: item.font || 'Arabic',
                    fontEn: item.fontEn || 'English',
                    translationLang: item.translationLang || 'en',
                    wordHighlight: item.wordHighlight ?? false,
                    fps: item.fps || 20,
                    quality: item.quality || '720',
                    bgQuery: item.bgQuery || '',
                    scenePack: item.scenePack || 'nature_calm',
                    bgCrossfadeSec: item.bgCrossfadeSec ?? 0.5,
                    adaptiveTextContrast: item.adaptiveTextContrast ?? true,
                    safeAreaGuides: item.safeAreaGuides ?? false,
                    safeAreaPaddingPx: item.safeAreaPaddingPx ?? 48,
                    audioProfile: item.audioProfile || 'studio',
                    audioDenoise: item.audioDenoise ?? false,
                    audioDeEss: item.audioDeEss ?? false
                })),
                pexelsKey: localStorage.getItem('user_pexels_key') || '',
                scenePack: document.getElementById('scenePack')?.value || 'nature_calm',
                bgCrossfadeSec: parseFloat(document.getElementById('bgCrossfadeSec')?.value || '0.5'),
                adaptiveTextContrast: document.getElementById('adaptiveTextContrast')?.checked ?? true,
                safeAreaGuides: document.getElementById('safeAreaGuides')?.checked ?? false,
                safeAreaPaddingPx: parseInt(document.getElementById('safeAreaPaddingPx')?.value || '48'),
                audioProfile: document.getElementById('audioProfile')?.value || 'studio',
                audioDenoise: document.getElementById('audioDenoise')?.checked ?? false,
                audioDeEss: document.getElementById('audioDeEss')?.checked ?? false,
                style: getStyleSettings()
            };
            
            try {
                showToast(t('creatingBatch'), 'success');
                
                const res = await fetch('/api/batch/create', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                if (!res.ok) {
                    throw new Error(`HTTP error! status: ${res.status}`);
                }
                
                const data = await res.json();
                
                if (data.ok) {
                    currentBatchId = data.batchId;
                    showToast(t('batchCreated', { count: data.totalJobs }), 'success');
                    
                    const statusSection = document.getElementById('batchStatusSection');
                    const totalCount = document.getElementById('batchTotalCount');
                    const completedCount = document.getElementById('batchCompletedCount');
                    
                    if (statusSection) statusSection.style.display = 'block';
                    if (totalCount) totalCount.textContent = data.totalJobs;
                    if (completedCount) completedCount.textContent = 0;
                    
                    startBatchPolling(data.batchId);
                    
                    batchItems = [];
                    renderBatchList();
                } else {
                    showToast(data.error || t('batchCreateFailed'), 'error');
                }
            } catch (err) {
                console.error('Batch creation error:', err);
            }
        }

        function cancelBatch() {
            if (!currentBatchId) return;
            
            batchCancelled = true;
            
            fetch('/api/batch/cancel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ batchId: currentBatchId, sessionId: SESSION_ID, lang: CURRENT_LANG })
            });
            
            showToast(t('batchCancelled'), 'error');
        }

        let batchPollInterval = null;

        function startBatchPolling(batchId) {
            if (batchPollInterval) clearInterval(batchPollInterval);
            
            batchPollInterval = setInterval(async () => {
                if (batchCancelled) {
                    clearInterval(batchPollInterval);
                    return;
                }
                
                try {
                    const res = await fetch(`/api/batch/status?batchId=${encodeURIComponent(batchId)}&sessionId=${encodeURIComponent(SESSION_ID)}&lang=${encodeURIComponent(CURRENT_LANG)}`);
                    const data = await res.json();
                    
                    if (data.ok) {
                        updateBatchProgress(data.batch);
                        
                        if (data.batch.status === 'complete' || data.batch.status === 'cancelled') {
                            clearInterval(batchPollInterval);
                            
                            if (data.batch.status === 'complete') {
                                showToast(t('batchCreatedDone', { count: data.batch.completedJobs }), 'success');
                                loadHistory();
                            }
                        }
                    }
                } catch (err) {
                    console.error('Batch polling error:', err);
                }
            }, 2000);
        }

        function updateBatchProgress(batch) {
            const total = batch.totalJobs;
            const completed = batch.completedJobs || 0;
            const failed = batch.failedJobs || 0;
            const percent = total > 0 ? Math.round(((completed + failed) / total) * 100) : 0;
            
            const circle = document.getElementById('batchProgressCircle');
            const circumference = 2 * Math.PI * 65;
            if (circle) {
                circle.style.strokeDashoffset = circumference - (percent / 100) * circumference;
            }
            
            document.getElementById('batchProgressPercent').textContent = `${percent}%`;
            document.getElementById('batchCompletedCount').textContent = completed + failed;
            
            const statusEl = document.getElementById('batchProgressStatus');
            const currentVideoEl = document.getElementById('batchCurrentVideo');
            const currentVideoNameEl = document.getElementById('batchCurrentVideoName');
            const remainingTimeEl = document.getElementById('batchRemainingTime');
            const remainingTimeValueEl = document.getElementById('batchRemainingTimeValue');
            
            if (batch.status === 'running') {
                statusEl.textContent = t('processingRunning', { current: batch.currentJobIndex + 1, total });
                
                // عرض الفيديو الحالي
                if (batch.currentVideo) {
                    currentVideoEl.style.display = 'block';
                    currentVideoNameEl.textContent = `${batch.currentVideo.surahName} - ${t('ayahWord')} ${batch.currentVideo.ayah}`;
                } else {
                    currentVideoEl.style.display = 'none';
                }
                
                // عرض الوقت المتبقي
                if (batch.remainingTime !== null && batch.remainingTime !== undefined) {
                    remainingTimeEl.style.display = 'block';
                    remainingTimeValueEl.textContent = formatTime(batch.remainingTime);
                } else {
                    remainingTimeEl.style.display = 'none';
                }
            } else if (batch.status === 'complete') {
                statusEl.textContent = t('completed');
                currentVideoEl.style.display = 'none';
                remainingTimeEl.style.display = 'none';
            } else if (batch.status === 'cancelled') {
                statusEl.textContent = t('cancelled');
                currentVideoEl.style.display = 'none';
                remainingTimeEl.style.display = 'none';
            } else if (batch.status === 'pending') {
                statusEl.textContent = t('waiting');
                currentVideoEl.style.display = 'none';
                remainingTimeEl.style.display = 'none';
            }
        }
        
        function formatTime(seconds) {
            if (seconds < 60) {
                return `${seconds} ${CURRENT_LANG === 'ar' ? t('secondWord') : t('secShort')}`;
            }
            const mins = Math.floor(seconds / 60);
            const secs = seconds % 60;
            if (mins >= 60) {
                const hours = Math.floor(mins / 60);
                const remainMins = mins % 60;
                return CURRENT_LANG === 'ar'
                    ? `${hours} ${t('hourWord')} ${remainMins} ${t('minShort')}`
                    : `${hours} ${t('hourShort')} ${remainMins} ${t('minShort')}`;
            }
            return `${mins} ${t('minShort')} ${secs} ${t('secShort')}`;
        }

        function initBatchPage() {
            const batchSurahSelect = document.getElementById('batchSurahSelect');
            const mainSurahSelect = document.getElementById('surahSelect');
            
            if (batchSurahSelect && mainSurahSelect) {
                batchSurahSelect.innerHTML = mainSurahSelect.innerHTML;
                
                batchSurahSelect.addEventListener('change', () => {
                    const max = VERSE_COUNTS[parseInt(batchSurahSelect.value)] || 286;
                    document.getElementById('batchStartAyah').value = 1;
                    document.getElementById('batchEndAyah').value = Math.min(5, max);
                });
            }
            
            const batchReciterSelect = document.getElementById('batchReciterSelect');
            const mainReciterSelect = document.getElementById('reciterSelect');
            
            if (batchReciterSelect && mainReciterSelect) {
                batchReciterSelect.innerHTML = mainReciterSelect.innerHTML;
            }

            // 🎤 تهيئة checkboxes القراء للعشوائي
            initReciterCheckboxes();
        }

        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                if (btn.dataset.tab === 'batch') {
                    initBatchPage();
                }
            });
        });

        async function checkActiveBatch() {
            try {
                const res = await fetch(`/api/batch/list?sessionId=${encodeURIComponent(SESSION_ID)}`);
                const data = await res.json();
                
                if (data.ok && data.batches) {
                    const activeBatch = data.batches.find(b => 
                        b.status === 'pending' || b.status === 'running'
                    );
                    
                    if (activeBatch) {
                        currentBatchId = activeBatch.id;
                        document.getElementById('batchStatusSection').style.display = 'block';
                        document.getElementById('batchTotalCount').textContent = activeBatch.totalJobs;
                        startBatchPolling(activeBatch.id);
                    }
                }
            } catch (err) {
                console.log('No active batches');
            }
        }

        setTimeout(checkActiveBatch, 1000);

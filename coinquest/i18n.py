# -*- coding: utf-8 -*-
"""Dil desteği: Türkmençe (varsayılan), Rusça, Türkçe.

Yeni yazı eklemek için STR sözlüğüne anahtar ekle:
    "anahtar": {"tk": "...", "ru": "...", "tr": "..."}
Kullanımı:  i18n.t(lang, "anahtar", isim="Ali")
"""
import db

DEFAULT = "tk"
LANGS = {
    "tk": "🇹🇲 Türkmençe",
    "ru": "🇷🇺 Русский",
    "tr": "🇹🇷 Türkçe",
}

STR: dict[str, dict[str, str]] = {

    # ---------- ALT BUTONLAR ----------
    "b_play":    {"tk": "🎮 Oýnamak",     "ru": "🎮 Играть",       "tr": "🎮 Oyna"},
    "b_money":   {"tk": "💵 Pul",          "ru": "💵 Деньги",       "tr": "💵 Para"},
    "b_gift":    {"tk": "🎁 Sowgat",       "ru": "🎁 Подарок",      "tr": "🎁 Hediye"},
    "b_shop":    {"tk": "🏪 Dükan",        "ru": "🏪 Магазин",      "tr": "🏪 Market"},
    "b_items":   {"tk": "🎒 Zatlarym",     "ru": "🎒 Мои вещи",     "tr": "🎒 Eşyalarım"},
    "b_friends": {"tk": "👥 Dost çagyr",   "ru": "👥 Позвать друга", "tr": "👥 Arkadaş Çağır"},
    "b_menu":    {"tk": "📖 Menýu",        "ru": "📖 Меню",         "tr": "📖 Menü"},

    # ---------- ORTAK BUTONLAR ----------
    "b_more":    {"tk": "⚙️ Başgalary",    "ru": "⚙️ Ещё",          "tr": "⚙️ Diğerleri"},
    "b_back":    {"tk": "⬅️ Yzyna",        "ru": "⬅️ Назад",        "tr": "⬅️ Geri"},
    "b_home":    {"tk": "🏠 Baş menýu",    "ru": "🏠 Главное меню",  "tr": "🏠 Ana menü"},
    "b_again":   {"tk": "🔄 Ýene oýna",    "ru": "🔄 Ещё раз",      "tr": "🔄 Tekrar oyna"},
    "b_refresh": {"tk": "🔄 Täzele",       "ru": "🔄 Обновить",     "tr": "🔄 Yenile"},
    "b_lang":    {"tk": "🌐 Dil",          "ru": "🌐 Язык",         "tr": "🌐 Dil"},
    "b_help":    {"tk": "❓ Nädip oýnamaly", "ru": "❓ Как играть",  "tr": "❓ Nasıl oynanır"},
    "b_duel":    {"tk": "⚔️ Duel",         "ru": "⚔️ Дуэль",        "tr": "⚔️ Düello"},
    "b_bank":    {"tk": "🏦 Bank",         "ru": "🏦 Банк",         "tr": "🏦 Banka"},
    "b_clan":    {"tk": "🏰 Topar",        "ru": "🏰 Клан",         "tr": "🏰 Klan"},
    "b_top":     {"tk": "🏆 Öňdeligler",   "ru": "🏆 Топ игроков",  "tr": "🏆 Sıralama"},
    "b_quests":  {"tk": "📜 Ýumuşlar",     "ru": "📜 Задания",      "tr": "📜 Görevler"},
    "b_lottery": {"tk": "🎟 Bije",         "ru": "🎟 Лотерея",      "tr": "🎟 Çekiliş"},
    "b_boss":    {"tk": "🐉 Aždarha",      "ru": "🐉 Босс",         "tr": "🐉 Canavar"},
    "b_bazaar":  {"tk": "🛒 Bazar",        "ru": "🛒 Базар",        "tr": "🛒 Pazar"},
    "b_biz":     {"tk": "🏭 Işim",         "ru": "🏭 Мой бизнес",   "tr": "🏭 İş Yerim"},
    "b_profile": {"tk": "👤 Hasabym",      "ru": "👤 Мой профиль",  "tr": "👤 Hesabım"},

    # ---------- ANA MENÜ ----------
    "menu_hi":   {"tk": "Salam, <b>{name}</b>! 👋",
                  "ru": "Привет, <b>{name}</b>! 👋",
                  "tr": "Merhaba <b>{name}</b>! 👋"},
    "menu_ask":  {"tk": "Näme etmek isleýärsiň?",
                  "ru": "Что хочешь сделать?",
                  "tr": "Ne yapmak istersin?"},
    "menu_boss": {"tk": "🐉 <b>{name}</b> hüjüm edýär! Hemmämiz bilelikde uraly!",
                  "ru": "🐉 <b>{name}</b> напал! Бьём все вместе!",
                  "tr": "🐉 <b>{name}</b> saldırdı! Hep beraber vuralım!"},
    "menu_quest": {"tk": "🎁 <b>{n}</b> ýumuşyň gutardy — sylagyňy al!",
                   "ru": "🎁 <b>{n}</b> задания выполнены — забери награду!",
                   "tr": "🎁 <b>{n}</b> görevin bitti — ödülünü al!"},

    # ---------- CÜZDAN SATIRI ----------
    "w_coin":  {"tk": "Teňňe",  "ru": "Монеты",  "tr": "Coin"},
    "w_gem":   {"tk": "Almaz",  "ru": "Алмазы",  "tr": "Elmas"},
    "w_lvl":   {"tk": "Dereje", "ru": "Уровень", "tr": "Seviye"},
    "w_money": {"tk": "Hakyky pul", "ru": "Реальные деньги", "tr": "Gerçek para"},

    # ---------- KARŞILAMA ----------
    "welcome": {
        "tk": ("🏰 <b>HOŞ GELDIŇ!</b>\n\n"
               "<blockquote>Sowgadyň: <b>{coins}</b> 🪙 we <b>{gems}</b> 💎</blockquote>\n\n"
               "<b>Bu ýerde näme edilýär?</b>\n"
               "🎮 Oýna — teňňe gazan\n"
               "⚔️ Dostuň bilen ýaryş — onuň teňňesini al\n"
               "🏪 Dükandan ýarag al — güýçlen\n"
               "💵 Teňňäňi <b>hakyky pula</b> öwür\n\n"
               "👇 Aşakdaky düwmeleri ulan, hiç zat ýazmaly däl."),
        "ru": ("🏰 <b>ДОБРО ПОЖАЛОВАТЬ!</b>\n\n"
               "<blockquote>Твой подарок: <b>{coins}</b> 🪙 и <b>{gems}</b> 💎</blockquote>\n\n"
               "<b>Что тут делают?</b>\n"
               "🎮 Играешь — получаешь монеты\n"
               "⚔️ Соревнуешься с другом — забираешь его монеты\n"
               "🏪 Покупаешь оружие — становишься сильнее\n"
               "💵 Меняешь монеты на <b>реальные деньги</b>\n\n"
               "👇 Просто жми кнопки внизу, писать ничего не надо."),
        "tr": ("🏰 <b>HOŞ GELDİN!</b>\n\n"
               "<blockquote>Hediyen: <b>{coins}</b> 🪙 ve <b>{gems}</b> 💎</blockquote>\n\n"
               "<b>Burada ne yapılır?</b>\n"
               "🎮 Oyna — coin kazan\n"
               "⚔️ Arkadaşınla yarış — onun coinini al\n"
               "🏪 Marketten silah al — güçlen\n"
               "💵 Coinini <b>gerçek paraya</b> çevir\n\n"
               "👇 Aşağıdaki butonları kullan, bir şey yazmana gerek yok."),
    },
    "ready": {"tk": "👇 Düwmeler taýýar.", "ru": "👇 Кнопки готовы.", "tr": "👇 Butonlar hazır."},

    # ---------- DİL ----------
    "lang_title": {"tk": "🌐 <b>Dil saýla</b>", "ru": "🌐 <b>Выбери язык</b>",
                   "tr": "🌐 <b>Dil seç</b>"},
    "lang_ok":    {"tk": "✅ Dil türkmençä çalşyryldy!", "ru": "✅ Язык изменён на русский!",
                   "tr": "✅ Dil Türkçe olarak ayarlandı!"},

    # ---------- PARA ----------
    "m_title": {"tk": "💵 <b>HAKYKY PUL</b>", "ru": "💵 <b>РЕАЛЬНЫЕ ДЕНЬГИ</b>",
                "tr": "💵 <b>GERÇEK PARA</b>"},
    "m_yours": {"tk": "💰 Puluň", "ru": "💰 Твои деньги", "tr": "💰 Paran"},
    "m_coins": {"tk": "🪙 Teňňäň", "ru": "🪙 Твои монеты", "tr": "🪙 Coinin"},
    "m_today": {"tk": "📅 Şu gün öwrüp bilýän", "ru": "📅 Сегодня можно обменять",
                "tr": "📅 Bugün çevirebileceğin"},
    "m_need":  {"tk": "🎯 Çykarmak üçin gerek", "ru": "🎯 Нужно для вывода",
                "tr": "🎯 Çekmek için gereken"},
    "m_left":  {"tk": "ýene {v} gerek", "ru": "ещё {v}", "tr": "daha {v} lazım"},
    "m_ready": {"tk": "✅ taýýar!", "ru": "✅ готово!", "tr": "✅ hazır!"},
    "m_how": {
        "tk": ("<blockquote><b>Nähili işleýär?</b>\n"
               "1️⃣ Oýnaýarsyň, teňňe ýygnaýarsyň\n"
               "2️⃣ Teňňäni pula öwürýärsiň ({coins} 🪙 = 1.00 {cur})\n"
               "3️⃣ Günde iň köp {cap} öwrüp bolýar\n"
               "4️⃣ {min} bolanda pul soraýarsyň</blockquote>\n\n"
               "<i>Günlük çäk sebäpli {min} iň az 8 günde ýygnanýar. "
               "Ýagny her gün gelip oýnamaly 😊</i>"),
        "ru": ("<blockquote><b>Как это работает?</b>\n"
               "1️⃣ Играешь, копишь монеты\n"
               "2️⃣ Меняешь монеты на деньги ({coins} 🪙 = 1.00 {cur})\n"
               "3️⃣ В день можно обменять максимум {cap}\n"
               "4️⃣ Набрал {min} — запрашиваешь выплату</blockquote>\n\n"
               "<i>Из-за дневного лимита {min} копится минимум 8 дней. "
               "То есть надо заходить каждый день 😊</i>"),
        "tr": ("<blockquote><b>Nasıl çalışır?</b>\n"
               "1️⃣ Oynarsın, coin toplarsın\n"
               "2️⃣ Coini paraya çevirirsin ({coins} 🪙 = 1.00 {cur})\n"
               "3️⃣ Günde en fazla {cap} çevirebilirsin\n"
               "4️⃣ {min} olunca ödeme istersin</blockquote>\n\n"
               "<i>Günlük limit yüzünden {min} en az 8 günde dolar. "
               "Yani her gün gelip oynaman lazım 😊</i>"),
    },
    "m_conv":  {"tk": "🔁 {coins} teňňe ➜ {money}", "ru": "🔁 {coins} монет ➜ {money}",
                "tr": "🔁 {coins} coin ➜ {money}"},
    "m_max":   {"tk": "⚡ Şu günki çäge çenli öwür", "ru": "⚡ Обменять до дневного лимита",
                "tr": "⚡ Bugünlük limiti doldur"},
    "m_full":  {"tk": "✅ Şu günki çäk doldy", "ru": "✅ Дневной лимит исчерпан",
                "tr": "✅ Bugünlük limit doldu"},
    "m_wd":    {"tk": "💸 Pul çykarmak", "ru": "💸 Вывести деньги", "tr": "💸 Para çek"},
    "m_hist":  {"tk": "📜 Taryh", "ru": "📜 История", "tr": "📜 Geçmiş"},
    "m_cap_hit": {"tk": "Şu günki çäk doldy. Ertir dowam et! 🙂",
                  "ru": "Дневной лимит исчерпан. Продолжим завтра! 🙂",
                  "tr": "Bugünlük limit doldu. Yarın devam! 🙂"},
    "m_no_coins": {"tk": "Teňňäň ýetenok. Biraz oýna! 🎮",
                   "ru": "Не хватает монет. Поиграй ещё! 🎮",
                   "tr": "Coinin yetmiyor. Biraz oyna! 🎮"},
    "m_done":  {"tk": "✅ {coins} teňňe ➜ {money}\n💰 Jemi puluň: {total}",
                "ru": "✅ {coins} монет ➜ {money}\n💰 Всего: {total}",
                "tr": "✅ {coins} coin ➜ {money}\n💰 Toplam paran: {total}"},
    "m_rules": {"tk": "<b>Şertler</b>\n• Iň az {min} ýygna\n• {lvl}-nji dereje bol\n• Hasabyň {days} günlük bolsun",
                "ru": "<b>Условия</b>\n• Накопить минимум {min}\n• Достичь {lvl} уровня\n• Аккаунту {days} дней",
                "tr": "<b>Şartlar</b>\n• En az {min} biriktir\n• Seviye {lvl} ol\n• Hesabın {days} günlük olsun"},
    "m_not_yet": {"tk": "❌ Entek bolanok:", "ru": "❌ Пока нельзя:", "tr": "❌ Henüz olmaz:"},
    "m_ask_amount": {"tk": "Näçe pul çykarmak isleýärsiň?", "ru": "Сколько хочешь вывести?",
                     "tr": "Ne kadar çekmek istersin?"},
    "m_ask_method": {"tk": "Puly nädip almak isleýärsiň?", "ru": "Как хочешь получить деньги?",
                     "tr": "Parayı nasıl almak istersin?"},
    "m_all":   {"tk": "💸 Ählisi", "ru": "💸 Всё", "tr": "💸 Hepsi"},
    "m_last":  {"tk": "💸 <b>SOŇKY ÄDIM</b>\n\nMukdar: <b>{amount}</b>\nUsul: {method}\n\nIndi <b>{what}</b> ýaz we ugrat.",
                "ru": "💸 <b>ПОСЛЕДНИЙ ШАГ</b>\n\nСумма: <b>{amount}</b>\nСпособ: {method}\n\nТеперь напиши <b>{what}</b> и отправь.",
                "tr": "💸 <b>SON ADIM</b>\n\nTutar: <b>{amount}</b>\nYöntem: {method}\n\nŞimdi <b>{what}</b> yaz ve gönder."},
    "m_cancel": {"tk": "⬅️ Goý bolsun", "ru": "⬅️ Отмена", "tr": "⬅️ Vazgeç"},
    "m_req_ok": {"tk": ("✅ <b>ARZAŇ KABUL EDILDI!</b>\n\n<blockquote>💵 Mukdar: <b>{amount}</b>\n"
                        "📮 Usul: {method}\n🔖 Arza belgisi: #{id}</blockquote>\n\n"
                        "Ýolbaşçy tiz wagtda tölär. Töleg edilende saňa habar geler."),
                 "ru": ("✅ <b>ЗАЯВКА ПРИНЯТА!</b>\n\n<blockquote>💵 Сумма: <b>{amount}</b>\n"
                        "📮 Способ: {method}\n🔖 Номер заявки: #{id}</blockquote>\n\n"
                        "Админ скоро выплатит. Придёт сообщение после оплаты."),
                 "tr": ("✅ <b>TALEBİN ALINDI!</b>\n\n<blockquote>💵 Tutar: <b>{amount}</b>\n"
                        "📮 Yöntem: {method}\n🔖 Talep no: #{id}</blockquote>\n\n"
                        "Yönetici en kısa sürede ödeyecek. Ödeme yapılınca haber gelir.")},
    "m_hist_title": {"tk": "📜 <b>PUL ÇYKARYŞ TARYHY</b>", "ru": "📜 <b>ИСТОРИЯ ВЫПЛАТ</b>",
                     "tr": "📜 <b>ÇEKİM GEÇMİŞİN</b>"},
    "m_hist_empty": {"tk": "Entek arzaň ýok.", "ru": "Заявок пока нет.", "tr": "Henüz talebin yok."},
    "m_paid_total": {"tk": "✅ Şu wagta çenli tölenen", "ru": "✅ Выплачено всего",
                     "tr": "✅ Bugüne kadar ödenen"},
    "m_paid": {"tk": ("✅ <b>PULUŇ TÖLENDI!</b>\n\n💵 {amount} ugradyldy.\n🔖 Arza #{id}\n\n"
                      "Oýnamagy dowam et! 🎮"),
               "ru": ("✅ <b>ДЕНЬГИ ВЫПЛАЧЕНЫ!</b>\n\n💵 {amount} отправлено.\n🔖 Заявка #{id}\n\n"
                      "Продолжай играть! 🎮"),
               "tr": ("✅ <b>PARAN ÖDENDİ!</b>\n\n💵 {amount} gönderildi.\n🔖 Talep #{id}\n\n"
                      "Oynamaya devam! 🎮")},
    "m_rejected": {"tk": "❌ <b>Arzaň ret edildi.</b>\n\n💵 {amount} hasabyňa gaýtaryldy.\n🔖 Arza #{id}",
                   "ru": "❌ <b>Заявка отклонена.</b>\n\n💵 {amount} возвращено на счёт.\n🔖 Заявка #{id}",
                   "tr": "❌ <b>Talebin reddedildi.</b>\n\n💵 {amount} hesabına geri yüklendi.\n🔖 Talep #{id}"},

    # ---------- ÖDEME YÖNTEMLERİ ----------
    "pm_card":  {"tk": "💳 Bank karty", "ru": "💳 Банковская карта", "tr": "💳 Banka kartı"},
    "pm_phone": {"tk": "📱 Telefon belgisi", "ru": "📱 Номер телефона", "tr": "📱 Telefon numarası"},
    "pm_other": {"tk": "✍️ Başga", "ru": "✍️ Другое", "tr": "✍️ Diğer"},
    "pm_card_ask":  {"tk": "kart belgiňi", "ru": "номер карты", "tr": "kart numaranı"},
    "pm_phone_ask": {"tk": "telefon belgiňi", "ru": "номер телефона", "tr": "telefon numaranı"},
    "pm_other_ask": {"tk": "töleg maglumatyňy", "ru": "данные для оплаты", "tr": "ödeme bilgini"},

    # ---------- OYUNLAR ----------
    "g_title": {"tk": "🎮 <b>OÝUNLAR</b>", "ru": "🎮 <b>ИГРЫ</b>", "tr": "🎮 <b>OYUNLAR</b>"},
    "g_pick":  {"tk": "Haýsy oýun? 👇", "ru": "Какая игра? 👇", "tr": "Hangi oyun? 👇"},
    "g_luck":  {"tk": "🎲 Şans oýunlary", "ru": "🎲 Игры на удачу", "tr": "🎲 Şans oyunları"},
    "g_brain": {"tk": "🧠 Akyl oýunlary", "ru": "🧠 Игры на ум", "tr": "🧠 Bilgi oyunları"},
    "g_work":  {"tk": "⚒ Iş oýunlary", "ru": "⚒ Работа", "tr": "⚒ İş oyunları"},
    "g_luck_info":  {"tk": "Teňňe goýýarsyň — köpeldip ýa-da ýitirip bilersiň.",
                     "ru": "Ставишь монеты — можешь умножить или потерять.",
                     "tr": "Coin koyarsın — katlarsın ya da kaybedersin."},
    "g_brain_info": {"tk": "Mugt. Ýitirmersiň, diňe gazanarsyň.",
                     "ru": "Бесплатно. Не потеряешь, только выиграешь.",
                     "tr": "Bedava. Kaybetmezsin, sadece kazanırsın."},
    "g_work_info":  {"tk": "Belli wagtdan bir gezek — hökman gazanç.",
                     "ru": "Раз в определённое время — гарантированный доход.",
                     "tr": "Belli aralıklarla — kesin kazanç."},
    "g_bet_range": {"tk": "💵 Goýup bolýan teňňe: {min} – {max}",
                    "ru": "💵 Ставка: от {min} до {max}",
                    "tr": "💵 Koyabileceğin coin: {min} – {max}"},
    "g_choose_bet": {"tk": "Näçe teňňe goýýarsyň? 👇", "ru": "Сколько монет ставишь? 👇",
                     "tr": "Kaç coin koyuyorsun? 👇"},
    "g_win":  {"tk": "🎉 <b>UTDUŇ!</b>", "ru": "🎉 <b>ТЫ ВЫИГРАЛ!</b>", "tr": "🎉 <b>KAZANDIN!</b>"},
    "g_lose": {"tk": "😔 <b>Utuldyň.</b>", "ru": "😔 <b>Проиграл.</b>", "tr": "😔 <b>Kaybettin.</b>"},

    # ---------- HEDİYE ----------
    "d_title": {"tk": "🎁 <b>GÜNDELIK SOWGAT</b>", "ru": "🎁 <b>ЕЖЕДНЕВНЫЙ ПОДАРОК</b>",
                "tr": "🎁 <b>GÜNLÜK HEDİYE</b>"},
    "d_streak": {"tk": "🔥 Yzygiderli: <b>{n}</b> gün", "ru": "🔥 Подряд: <b>{n}</b> дней",
                 "tr": "🔥 Üst üste: <b>{n}</b> gün"},
    "d_note": {"tk": "<i>Her gün gel — sowgat ulalýar.</i>",
               "ru": "<i>Заходи каждый день — подарок растёт.</i>",
               "tr": "<i>Her gün gel — hediye büyür.</i>"},
    "d_wait": {"tk": "⏳ Sowgadyňy aldyň. Täzesi: <b>{time}</b>",
               "ru": "⏳ Подарок уже получен. Следующий через: <b>{time}</b>",
               "tr": "⏳ Hediyeni aldın. Yenisi: <b>{time}</b>"},

    # ---------- YARDIM ----------
    "h_title": {"tk": "❓ <b>NÄDIP OÝNAMALY?</b>", "ru": "❓ <b>КАК ИГРАТЬ?</b>",
                "tr": "❓ <b>NASIL OYNANIR?</b>"},
    "h_body": {
        "tk": ("<blockquote><b>1️⃣ Teňňe gazan</b>\n"
               "🎮 Oýna, 🎁 her gün sowgat al, 💼 işle, ⛏ magdan gaz.</blockquote>\n\n"
               "<blockquote><b>2️⃣ Güýçlen</b>\n"
               "🏪 Ýarag-galkan al, ⚔️ dostuň bilen ýaryş, 🐉 aždarhany bilelikde ur.</blockquote>\n\n"
               "<blockquote><b>3️⃣ Pul al</b>\n"
               "💵 Teňňäňi hakyky pula öwür, ýygnanda töleg sora.</blockquote>\n\n"
               "<i>Hemme zat düwme bilen — hiç zat ýazmaly däl 👇</i>"),
        "ru": ("<blockquote><b>1️⃣ Зарабатывай монеты</b>\n"
               "🎮 Играй, 🎁 забирай подарок каждый день, 💼 работай, ⛏ копай шахту.</blockquote>\n\n"
               "<blockquote><b>2️⃣ Становись сильнее</b>\n"
               "🏪 Покупай оружие, ⚔️ соревнуйся с друзьями, 🐉 бейте босса вместе.</blockquote>\n\n"
               "<blockquote><b>3️⃣ Получай деньги</b>\n"
               "💵 Меняй монеты на реальные деньги и запрашивай выплату.</blockquote>\n\n"
               "<i>Всё делается кнопками — писать ничего не нужно 👇</i>"),
        "tr": ("<blockquote><b>1️⃣ Coin kazan</b>\n"
               "🎮 Oyna, 🎁 her gün hediye al, 💼 çalış, ⛏ maden kaz.</blockquote>\n\n"
               "<blockquote><b>2️⃣ Güçlen</b>\n"
               "🏪 Silah-zırh al, ⚔️ arkadaşınla yarış, 🐉 canavarı birlikte dövün.</blockquote>\n\n"
               "<blockquote><b>3️⃣ Para al</b>\n"
               "💵 Coinini gerçek paraya çevir, birikince ödeme iste.</blockquote>\n\n"
               "<i>Her şey butonlarla — bir şey yazmana gerek yok 👇</i>"),
    },

    # ---------- DİĞERLERİ MENÜSÜ ----------
    "more_title": {"tk": "⚙️ <b>BAŞGA BÖLÜMLER</b>", "ru": "⚙️ <b>ДРУГИЕ РАЗДЕЛЫ</b>",
                   "tr": "⚙️ <b>DİĞER BÖLÜMLER</b>"},

    # ---------- GRUP / DÜELLO ----------
    "duel_private": {"tk": "⚔️ Duelller toparlarda bolýar. Meni dostlaryň topara goş!",
                     "ru": "⚔️ Дуэли проходят в группах. Добавь меня в группу с друзьями!",
                     "tr": "⚔️ Düellolar gruplarda olur. Beni arkadaş grubuna ekle!"},
    "only_private": {"tk": "Bu bölüm diňe maňa şahsy ýazanyňda açylýar 🙂",
                     "ru": "Этот раздел открывается только в личном чате 🙂",
                     "tr": "Bu bölüm sadece bana özelden yazınca açılır 🙂"},
}


def t(lang: str, key: str, **kw) -> str:
    """Anahtarın karşılığını verilen dilde döner; yoksa Türkmençeye düşer."""
    entry = STR.get(key)
    if not entry:
        return key
    text = entry.get(lang) or entry.get(DEFAULT) or next(iter(entry.values()))
    if kw:
        try:
            return text.format(**kw)
        except (KeyError, IndexError):
            return text
    return text


def lang_of(user_id: int) -> str:
    """Kullanıcının seçtiği dil (yoksa varsayılan)."""
    row = db.one("SELECT lang FROM users WHERE user_id=?", (user_id,))
    if row and row["lang"] in LANGS:
        return row["lang"]
    return DEFAULT


def set_lang(user_id: int, lang: str) -> None:
    if lang in LANGS:
        db.upd(user_id, lang=lang)


def all_button_labels() -> dict[str, str]:
    """Bütün dillerdeki alt buton yazıları -> anahtar eşlemesi."""
    keys = ["b_play", "b_money", "b_gift", "b_shop", "b_items", "b_friends", "b_menu"]
    out = {}
    for key in keys:
        for lang in LANGS:
            out[t(lang, key)] = key
    return out

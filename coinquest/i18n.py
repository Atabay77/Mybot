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
    "b_war":     {"tk": "⚔️ Topar Söweşi", "ru": "⚔️ Битва кланов", "tr": "⚔️ Klan Savaşı"},
    "b_notify":  {"tk": "🔔 Habarnamalar", "ru": "🔔 Уведомления",  "tr": "🔔 Bildirimler"},
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
    # ---------- DESTEK ----------
    "b_support": {"tk": "🆘 Kömek gullugy", "ru": "🆘 Поддержка", "tr": "🆘 Destek"},
    "sup_title": {"tk": "🆘 <b>KÖMEK GULLUGY</b>", "ru": "🆘 <b>ПОДДЕРЖКА</b>",
                  "tr": "🆘 <b>DESTEK</b>"},
    "sup_info": {"tk": "<blockquote>Soragyň, kynçylygyň ýa-da teklibiň barmy?\n"
                       "Ýaz — ýolbaşçy jogap berer.\nSurat, wideo hem ugradyp bilersiň.</blockquote>",
                 "ru": "<blockquote>Есть вопрос, проблема или предложение?\n"
                       "Напиши — админ ответит.\nМожно отправлять фото и видео.</blockquote>",
                 "tr": "<blockquote>Sorun, sorun ya da önerin mi var?\n"
                       "Yaz — yönetici cevaplayacak.\nFotoğraf, video da gönderebilirsin.</blockquote>"},
    "sup_write": {"tk": "✍️ Habar ýaz", "ru": "✍️ Написать", "tr": "✍️ Mesaj yaz"},
    "sup_ask": {"tk": "Habaryňy ýaz we ugrat 👇\n<i>Surat, wideo, ses — hemmesi bolýar.</i>",
                "ru": "Напиши сообщение и отправь 👇\n<i>Фото, видео, голос — всё можно.</i>",
                "tr": "Mesajını yaz ve gönder 👇\n<i>Fotoğraf, video, ses — hepsi olur.</i>"},
    "sup_sent": {"tk": "✅ Habaryň ugradyldy! Jogap gelende habar ederin.",
                 "ru": "✅ Сообщение отправлено! Ответ придёт сюда.",
                 "tr": "✅ Mesajın gönderildi! Cevap buraya gelecek."},
    "sup_from_staff": {"tk": "🎧 <b>Kömek gullugyndan jogap:</b>",
                       "ru": "🎧 <b>Ответ поддержки:</b>",
                       "tr": "🎧 <b>Destekten cevap:</b>"},
    "sup_last": {"tk": "Soňky habarlar", "ru": "Последние сообщения", "tr": "Son mesajlar"},

    # ---------- BOT KORUMASI ----------
    "cap_title": {"tk": "🤖 <b>BOT DÄLDIGIŇI SUBUT ET</b>", "ru": "🤖 <b>ПОДТВЕРДИ, ЧТО ТЫ НЕ БОТ</b>",
                  "tr": "🤖 <b>BOT OLMADIĞINI KANITLA</b>"},
    "cap_ask": {"tk": "Aşakdaky sowagyň jogabyny saýla:", "ru": "Выбери правильный ответ:",
                "tr": "Doğru cevabı seç:"},
    "cap_ok": {"tk": "✅ Dogry! Oýna başlap bilersiň.", "ru": "✅ Верно! Можно играть.",
               "tr": "✅ Doğru! Oynamaya başlayabilirsin."},
    "cap_wrong": {"tk": "❌ Nädogry. Ýene synanyş ({n}/{max})", "ru": "❌ Неверно. Попробуй ещё ({n}/{max})",
                  "tr": "❌ Yanlış. Tekrar dene ({n}/{max})"},
    "cap_fail": {"tk": "🚫 Köp ýalňyş etdiň. Täze sowal:", "ru": "🚫 Слишком много ошибок. Новый вопрос:",
                 "tr": "🚫 Çok yanlış yaptın. Yeni soru:"},
    "cap_need": {"tk": "Öňürti bot däldigiňi subut et 👇", "ru": "Сначала подтверди, что ты не бот 👇",
                 "tr": "Önce bot olmadığını kanıtla 👇"},

    # ---------- PARA BİRİMİ ----------
    "cur_pick": {"tk": "Haýsy pulda almak isleýärsiň?", "ru": "В какой валюте хочешь получить?",
                 "tr": "Hangi para biriminde almak istersin?"},
    "cur_note": {"tk": "USDT CryptoBot arkaly ugradylýar.", "ru": "USDT отправляется через CryptoBot.",
                 "tr": "USDT, CryptoBot üzerinden gönderilir."},

    # ---------- ONLINE DÜELLO ----------
    "d_online": {"tk": "🌐 Onlaýn garşydaş tap", "ru": "🌐 Найти соперника онлайн",
                 "tr": "🌐 Online rakip bul"},
    "d_group": {"tk": "👥 Toparda duel gur", "ru": "👥 Дуэль в группе", "tr": "👥 Grupta düello kur"},
    "d_search": {"tk": "🔍 <b>Garşydaş gözlenýär...</b>\n\nOýun: {game}\nJedel: {stake} 🪙\n\n"
                       "<i>Biri tapylanda oýun awtomat başlar.</i>",
                 "ru": "🔍 <b>Ищем соперника...</b>\n\nИгра: {game}\nСтавка: {stake} 🪙\n\n"
                       "<i>Игра начнётся автоматически.</i>",
                 "tr": "🔍 <b>Rakip aranıyor...</b>\n\nOyun: {game}\nBahis: {stake} 🪙\n\n"
                       "<i>Biri bulununca oyun otomatik başlar.</i>"},
    "d_cancel": {"tk": "🚫 Gözlegi bes et", "ru": "🚫 Отменить поиск", "tr": "🚫 Aramayı iptal et"},
    "d_found": {"tk": "⚔️ <b>Garşydaş tapyldy!</b>", "ru": "⚔️ <b>Соперник найден!</b>",
                "tr": "⚔️ <b>Rakip bulundu!</b>"},
    "d_queued": {"tk": "Nobata goşuldyň, garaş...", "ru": "Ты в очереди, жди...",
                 "tr": "Sıraya girdin, bekle..."},
    "d_already": {"tk": "Bu oýun we jedel bilen eýýäm bir ilanyň bar. Başga jedel saýla.",
                  "ru": "У тебя уже есть заявка на эту игру с этой ставкой. Выбери другую ставку.",
                  "tr": "Bu oyun ve bahiste zaten açık ilanın var. Başka bahis seç."},
    "d_maxopen": {"tk": "Iň köp 5 açyk ilanyň bolup biler.", "ru": "Максимум 5 открытых заявок.",
                  "tr": "En fazla 5 açık ilanın olabilir."},
    "d_cancelled": {"tk": "🚫 Ilan(lar) ýatyryldy, {amount} 🪙 yzyna berildi.",
                    "ru": "🚫 Заявки отменены, {amount} 🪙 возвращено.",
                    "tr": "🚫 İlan(lar) iptal edildi, {amount} 🪙 iade edildi."},
    "d_cancel_all": {"tk": "🚫 Ählisini ýatyr", "ru": "🚫 Отменить все", "tr": "🚫 Hepsini iptal et"},
    "d_mine": {"tk": "📋 Meniň ilanlarym", "ru": "📋 Мои заявки", "tr": "📋 İlanlarım"},
    "d_list": {"tk": "📋 Açyk oýunlar", "ru": "📋 Открытые игры", "tr": "📋 Açık oyunlar"},
    "d_list_t": {"tk": "AÇYK OÝUNLAR", "ru": "ОТКРЫТЫЕ ИГРЫ", "tr": "AÇIK OYUNLAR"},
    "d_list_empty": {"tk": "Häzir garaşýan oýun ýok. Sen bir sanysyny aç, garşydaş geler! 👇",
                     "ru": "Сейчас нет открытых игр. Открой свою — соперник придёт! 👇",
                     "tr": "Şu anda bekleyen oyun yok. Sen bir tane aç, rakip gelsin! 👇"},
    "d_online_open": {"tk": "Onlaýn garaşýanlar (basyp goşul)",
                      "ru": "Ждут онлайн (нажми, чтобы войти)",
                      "tr": "Online bekleyenler (bas ve katıl)"},
    "d_group_open": {"tk": "Toparlardaky oýunlar", "ru": "Игры в группах", "tr": "Gruplardaki oyunlar"},

    # ---------- MADENCİLER ----------
    "b_miners": {"tk": "⛏ Magdanlarym", "ru": "⛏ Мои шахты", "tr": "⛏ Madenlerim"},
    "mn_title": {"tk": "⛏ <b>MAGDANLARYM</b>", "ru": "⛏ <b>МОИ ШАХТЫ</b>",
                 "tr": "⛏ <b>MADENLERİM</b>"},
    "mn_title_s": {"tk": "⛏ Magdanlar", "ru": "⛏ Шахты", "tr": "⛏ Madenler"},
    "mn_empty": {"tk": "Entek magdançyň ýok. Aşakdan satyn al we uklaňda-da gazan! 💤",
                 "ru": "У тебя пока нет шахтёров. Купи ниже и зарабатывай даже во сне! 💤",
                 "tr": "Henüz madencin yok. Aşağıdan satın al, uyurken bile kazan! 💤"},
    "mn_power": {"tk": "⚡ Umumy güýç: <b>{power}</b> 🪙 / 4 sagat",
                 "ru": "⚡ Общая мощность: <b>{power}</b> 🪙 / 4 часа",
                 "tr": "⚡ Toplam güç: <b>{power}</b> 🪙 / 4 saat"},
    "mn_power_s": {"tk": "Güýç", "ru": "Мощность", "tr": "Güç"},
    "mn_case": {"tk": "💰 Kassa (janly)", "ru": "💰 Касса (вживую)", "tr": "💰 Kasa (canlı)"},
    "mn_ready_c": {"tk": "✅ {cycles}/{max} tapgyr doldy — ýygnap bilersiň",
                   "ru": "✅ Заполнено {cycles}/{max} циклов — можно собрать",
                   "tr": "✅ {cycles}/{max} döngü doldu — toplayabilirsin"},
    "mn_alert": {"tk": "⛏ <b>Kassaň doldy!</b>\n\n💰 <b>{amount}</b> 🪙 ýygnamaga taýýar.",
                 "ru": "⛏ <b>Касса заполнена!</b>\n\n💰 <b>{amount}</b> 🪙 готово к сбору.",
                 "tr": "⛏ <b>Kasan doldu!</b>\n\n💰 <b>{amount}</b> 🪙 toplanmaya hazır."},
    "mn_ready": {"tk": "💰 <b>Ýygnamaga taýýar: {amount} 🪙</b> ({cycles} tapgyr)",
                 "ru": "💰 <b>Готово к сбору: {amount} 🪙</b> ({cycles} циклов)",
                 "tr": "💰 <b>Toplanmaya hazır: {amount} 🪙</b> ({cycles} döngü)"},
    "mn_next": {"tk": "⏳ Indiki ýygnama: {time}", "ru": "⏳ Следующий сбор: {time}",
                "tr": "⏳ Sonraki toplama: {time}"},
    "mn_full": {"tk": "⚠️ Kassa doldy! Ýygnamasaň köpelmez.",
                "ru": "⚠️ Касса заполнена! Пока не соберёшь, больше не копится.",
                "tr": "⚠️ Kasa doldu! Toplamazsan daha fazla birikmez."},
    "mn_collect": {"tk": "💰 KASSANY ÝYGNA", "ru": "💰 СОБРАТЬ", "tr": "💰 KASAYI TOPLA"},
    "mn_got": {"tk": "💰 +{amount} 🪙 ýygnadyň! ({cycles} tapgyr)",
               "ru": "💰 Собрано +{amount} 🪙! ({cycles} циклов)",
               "tr": "💰 +{amount} 🪙 topladın! ({cycles} döngü)"},
    "mn_wait": {"tk": "⏳ Kassa entek dolmady. {time} soň gel.",
                "ru": "⏳ Касса ещё не наполнилась. Приходи через {time}.",
                "tr": "⏳ Kasa henüz dolmadı. {time} sonra gel."},
    "mn_none": {"tk": "Öňürti magdançy satyn al.", "ru": "Сначала купи шахтёра.",
                "tr": "Önce madenci satın al."},
    "mn_buy": {"tk": "✅ SATYN AL", "ru": "✅ КУПИТЬ", "tr": "✅ SATIN AL"},
    "mn_price": {"tk": "Bahasy", "ru": "Цена", "tr": "Fiyat"},
    "mn_size": {"tk": "Boýy", "ru": "Размер", "tr": "Boyu"},
    "mn_stronger": {"tk": "Öňkiden <b>{x}x</b> güýçli", "ru": "В <b>{x}x</b> мощнее предыдущего",
                    "tr": "Öncekinden <b>{x}x</b> güçlü"},
    "mn_have": {"tk": "Sende bar", "ru": "У тебя", "tr": "Sende"},
    "mn_roi": {"tk": "Özüni {hours} sagatda ödeýär", "ru": "Окупается за {hours} часов",
               "tr": "Kendini {hours} saatte öder"},
    "mn_bought": {"tk": "✅ {name} alyndy! Indi ×{qty}  •  +{power} 🪙/4s",
                  "ru": "✅ {name} куплен! Теперь ×{qty}  •  +{power} 🪙/4ч",
                  "tr": "✅ {name} alındı! Artık ×{qty}  •  +{power} 🪙/4s"},
    "mn_level": {"tk": "🔒 {lvl}-nji dereje gerek.", "ru": "🔒 Нужен {lvl} уровень.",
                 "tr": "🔒 Seviye {lvl} gerekiyor."},
    "mn_how": {"tk": "<i>Her {hours} sagatda bir kassany ýygna. Iň köp {max} tapgyr birigýär.</i>",
               "ru": "<i>Собирай кассу каждые {hours} часа. Копится максимум {max} циклов.</i>",
               "tr": "<i>Her {hours} saatte bir kasayı topla. En fazla {max} döngü birikir.</i>"},

    # ---------- UYARILAR ----------
    "no_money": {"tk": "❌ Teňňäň ýetenok!\nGerek: {need} 🪙\nSende: {have} 🪙",
                 "ru": "❌ Не хватает монет!\nНужно: {need} 🪙\nУ тебя: {have} 🪙",
                 "tr": "❌ Coinin yetmiyor!\nGereken: {need} 🪙\nSende: {have} 🪙"},
    "no_gems": {"tk": "❌ Almazyň ýetenok! Gerek: {need} 💎",
                "ru": "❌ Не хватает алмазов! Нужно: {need} 💎",
                "tr": "❌ Elmasın yetmiyor! Gereken: {need} 💎"},

    "only_private": {"tk": "Bu bölüm diňe maňa şahsy ýazanyňda açylýar 🙂",
                     "ru": "Этот раздел открывается только в личном чате 🙂",
                     "tr": "Bu bölüm sadece bana özelden yazınca açılır 🙂"},

    # ---------- KLAN SAVAŞI ----------
    "w_toast": {"tk": "⚔️ Topar söweşi", "ru": "⚔️ Битва кланов", "tr": "⚔️ Klan Savaşı"},
    "w_title": {"tk": "⚔️ <b>TOPAR SÖWEŞI</b>", "ru": "⚔️ <b>БИТВА КЛАНОВ</b>",
                "tr": "⚔️ <b>KLAN SAVAŞI</b>"},
    "w_clans": {"tk": "topar", "ru": "кланов", "tr": "klan"},
    "w_rank": {"tk": "Orun", "ru": "Место", "tr": "Sıra"},
    "w_left": {"tk": "Galan wagt", "ru": "Осталось", "tr": "Kalan süre"},
    "w_my_points": {"tk": "Seniň balyň", "ru": "Твои очки", "tr": "Puanın"},
    "w_noclan": {"tk": "Sen entek topara girmediň. Toparyň bolmasa-da baljaň ýygnanýar!",
                 "ru": "Ты ещё не в клане. Очки копятся и без клана!",
                 "tr": "Henüz bir klanda değilsin. Klansız da puanın birikiyor!"},
    "w_join_first": {"tk": "🏰 Topara giriň — toparyň ýeňse ähli agzalar sylag alýar.",
                     "ru": "🏰 Вступи в клан — при победе награду получают все участники.",
                     "tr": "🏰 Bir klana katıl — klan kazanınca bütün üyeler ödül alır."},
    "w_rival_ahead": {"tk": "Diňe <b>{gap}</b> bal öňde — kowala!",
                      "ru": "Всего на <b>{gap}</b> очков впереди — догоняй!",
                      "tr": "Sadece <b>{gap}</b> puan önde — yakala onları!"},
    "w_rival_behind": {"tk": "<b>{gap}</b> bal yzda", "ru": "отстаёт на <b>{gap}</b>",
                       "tr": "<b>{gap}</b> puan geride"},
    "w_leader": {"tk": "👑 Sen baştasyň! Ony saklap bil.",
                 "ru": "👑 Ты на первом месте! Удержи его.",
                 "tr": "👑 Birincisin! Sakın kaptırma."},
    "w_top_contrib": {"tk": "Iň köp goşant goşanlar", "ru": "Лучшие бойцы",
                      "tr": "En çok katkı verenler"},
    "w_my_share": {"tk": "👤 Seniň goşandyň: <b>{points}</b> ⭐",
                   "ru": "👤 Твой вклад: <b>{points}</b> ⭐",
                   "tr": "👤 Senin katkın: <b>{points}</b> ⭐"},
    "w_prize_teaser": {"tk": "🎁 Ilkinji 3 topar: hazyna + agzalara teňňe we almaz.",
                       "ru": "🎁 Топ-3 клана: казна + монеты и алмазы участникам.",
                       "tr": "🎁 İlk 3 klan: kasa + üyelere coin ve elmas."},
    "w_board_clan": {"tk": "⚔️ <b>TOPAR SÖWEŞI — ÖŇDELIK</b>",
                     "ru": "⚔️ <b>БИТВА КЛАНОВ — РЕЙТИНГ</b>",
                     "tr": "⚔️ <b>KLAN SAVAŞI — SIRALAMA</b>"},
    "w_board_player": {"tk": "🔥 <b>HEPDELIK ÖŇDELIK</b>", "ru": "🔥 <b>РЕЙТИНГ НЕДЕЛИ</b>",
                       "tr": "🔥 <b>HAFTALIK SIRALAMA</b>"},
    "w_board_empty": {"tk": "Bu hepde entek bal ýygnalmady.", "ru": "На этой неделе очков ещё нет.",
                      "tr": "Bu hafta henüz puan toplanmadı."},
    "w_you_are": {"tk": "📍 Sen: <b>#{rank}</b> — {points} ⭐",
                  "ru": "📍 Ты: <b>#{rank}</b> — {points} ⭐",
                  "tr": "📍 Sen: <b>#{rank}</b> — {points} ⭐"},
    "w_rules_title": {"tk": "📜 <b>BAL NÄDIP ÝYGNALÝAR</b>", "ru": "📜 <b>КАК ЗАРАБОТАТЬ ОЧКИ</b>",
                      "tr": "📜 <b>PUAN NASIL KAZANILIR</b>"},
    "w_rules_intro": {"tk": "Adaty oýnaýşyň ýaly oýna — bal öz-özünden ýygnanýar.",
                      "ru": "Просто играй как обычно — очки копятся сами.",
                      "tr": "Her zamanki gibi oyna — puan kendiliğinden birikir."},
    "w_cap": {"tk": "gün çägi", "ru": "лимит/день", "tr": "günlük tavan"},
    "w_rules_cap": {"tk": "ℹ️ Her çeşmäniň gün çägi bar — şonuň üçin diňe köp basmak ýeterlik däl.",
                    "ru": "ℹ️ У каждого источника дневной лимит — простым спамом не выиграть.",
                    "tr": "ℹ️ Her kaynağın günlük tavanı var — sadece çok basmak yetmez."},
    "w_rewards_title": {"tk": "🎁 <b>HEPDELIK SYLAGLAR</b>", "ru": "🎁 <b>НАГРАДЫ НЕДЕЛИ</b>",
                        "tr": "🎁 <b>HAFTALIK ÖDÜLLER</b>"},
    "w_rewards_player": {"tk": "🔥 Öňdeligiň ilkinji 10-y", "ru": "🔥 Топ-10 игроков",
                         "tr": "🔥 Sıralamanın ilk 10'u"},
    "w_rewards_clan": {"tk": "⚔️ Topar söweşiniň ilkinji 3-si", "ru": "⚔️ Топ-3 клана",
                       "tr": "⚔️ Klan savaşının ilk 3'ü"},
    "w_rewards_min": {"tk": "<i>Sylag üçin iň azyndan {points} bal gerek.</i>",
                      "ru": "<i>Для награды нужно минимум {points} очков.</i>",
                      "tr": "<i>Ödül için en az {points} puan gerekir.</i>"},
    "w_rewards_join": {"tk": "🤝 {points} bal ýygnan HERKIM: {coins} 🪙",
                       "ru": "🤝 Каждому, кто набрал {points} очков: {coins} 🪙",
                       "tr": "🤝 {points} puan toplayan HERKESE: {coins} 🪙"},
    "w_treasury": {"tk": "hazyna", "ru": "казна", "tr": "kasa"},
    "w_pool": {"tk": "agzalara", "ru": "участникам", "tr": "üyelere"},
    "w_leader_prize": {"tk": "baştutana {money}", "ru": "лидеру {money}", "tr": "lidere {money}"},
    "w_me_title": {"tk": "📊 <b>MENIŇ BALYM</b>", "ru": "📊 <b>МОИ ОЧКИ</b>",
                   "tr": "📊 <b>PUANIM</b>"},
    "w_me_today": {"tk": "Bu gün ýygnananlar", "ru": "Набрано сегодня", "tr": "Bugün kazandıkların"},
    "w_me_none": {"tk": "Bu gün entek bal ýok — oýna!", "ru": "Сегодня очков ещё нет — играй!",
                  "tr": "Bugün henüz puan yok — oyna!"},
    "w_me_hint": {"tk": "ℹ️ Çäge ýeteniňde şol çeşmeden bal gelmeýär, ertesi gün täzelenýär.",
                  "ru": "ℹ️ При достижении лимита источник не даёт очков до следующего дня.",
                  "tr": "ℹ️ Tavana ulaşınca o kaynaktan puan gelmez, ertesi gün yenilenir."},
    "w_last_title": {"tk": "🏅 <b>GEÇEN HEPDE</b>", "ru": "🏅 <b>ПРОШЛАЯ НЕДЕЛЯ</b>",
                     "tr": "🏅 <b>GEÇEN HAFTA</b>"},
    "w_last_none": {"tk": "Entek tamamlanan sezon ýok.", "ru": "Завершённых сезонов пока нет.",
                    "tr": "Henüz tamamlanmış sezon yok."},
    "w_b_board_c": {"tk": "⚔️ Topar öňdeligi", "ru": "⚔️ Рейтинг кланов",
                    "tr": "⚔️ Klan sıralaması"},
    "w_b_board_p": {"tk": "🔥 Hepdelik öňdelik", "ru": "🔥 Рейтинг недели",
                    "tr": "🔥 Haftalık sıralama"},
    "w_b_me": {"tk": "📊 Meniň balym", "ru": "📊 Мои очки", "tr": "📊 Puanım"},
    "w_b_rules": {"tk": "📜 Bal nädip", "ru": "📜 Как получить очки", "tr": "📜 Puan nasıl"},
    "w_b_rewards": {"tk": "🎁 Sylaglar", "ru": "🎁 Награды", "tr": "🎁 Ödüller"},
    "w_b_last": {"tk": "🏅 Geçen hepde", "ru": "🏅 Прошлая неделя", "tr": "🏅 Geçen hafta"},
    "w_b_war": {"tk": "⚔️ Söweş", "ru": "⚔️ Битва", "tr": "⚔️ Savaş"},
    "w_b_join": {"tk": "🏰 Topara gir", "ru": "🏰 Вступить в клан", "tr": "🏰 Klana katıl"},
    "menu_war": {"tk": "⚔️ Sezon gutarýar! Galan wagt: {time}",
                 "ru": "⚔️ Сезон заканчивается! Осталось: {time}",
                 "tr": "⚔️ Sezon bitiyor! Kalan süre: {time}"},
    # puan kaynaklarının adları
    "w_src_play": {"tk": "Oýun oýna", "ru": "Сыграть", "tr": "Oyun oyna"},
    "w_src_win": {"tk": "Oýun ut", "ru": "Выиграть", "tr": "Oyun kazan"},
    "w_src_wager": {"tk": "Goýlan teňňe", "ru": "Ставки", "tr": "Yapılan bahis"},
    "w_src_pvp": {"tk": "PVP ýeňşi", "ru": "Победа в PVP", "tr": "PVP galibiyeti"},
    "w_src_boss": {"tk": "Aždarha urgusy", "ru": "Удар по боссу", "tr": "Boss'a vuruş"},
    "w_src_work": {"tk": "Işlemek", "ru": "Работа", "tr": "Çalışmak"},
    "w_src_mine": {"tk": "Magdan gazmak", "ru": "Копать шахту", "tr": "Maden kazmak"},
    "w_src_skill": {"tk": "Başarnyk oýny", "ru": "Игра на умение", "tr": "Beceri oyunu"},
    "w_src_arena": {"tk": "Arena", "ru": "Арена", "tr": "Arena"},
    "w_src_buy": {"tk": "Dükandan al", "ru": "Покупка", "tr": "Market alışverişi"},
    "w_src_upgrade": {"tk": "Zat kämilleşdir", "ru": "Улучшение", "tr": "Eşya yükseltme"},
    "w_src_quest": {"tk": "Ýumuş tamamla", "ru": "Выполнить задание", "tr": "Görev tamamla"},
    "w_src_daily": {"tk": "Gündelik sowgat", "ru": "Ежедневный подарок", "tr": "Günlük hediye"},
    "w_src_miner": {"tk": "Magdançy ýygna", "ru": "Сбор с шахтёров", "tr": "Madenci topla"},
    "w_src_biz": {"tk": "Iş ýerini ýygna", "ru": "Сбор с бизнеса", "tr": "İşletme topla"},
    "w_src_donate": {"tk": "Topara sadaka", "ru": "Взнос в клан", "tr": "Klana bağış"},
    "w_src_ref": {"tk": "Dost çagyrmak", "ru": "Приглашение друга", "tr": "Arkadaş daveti"},

    # ---------- BİLDİRİMLER ----------
    "nt_toast": {"tk": "🔔 Habarnamalar", "ru": "🔔 Уведомления", "tr": "🔔 Bildirimler"},
    "nt_title": {"tk": "🔔 <b>HABARNAMALAR</b>", "ru": "🔔 <b>УВЕДОМЛЕНИЯ</b>",
                 "tr": "🔔 <b>BİLDİRİMLER</b>"},
    "nt_state_on": {"tk": "✅ Açyk — möhüm zatlary ýatladaryn.",
                    "ru": "✅ Включены — напомню о важном.",
                    "tr": "✅ Açık — önemli şeyleri hatırlatırım."},
    "nt_state_off": {"tk": "🔕 Öçük — hiç zat ýazmaryn.", "ru": "🔕 Выключены — писать не буду.",
                     "tr": "🔕 Kapalı — hiçbir şey yazmam."},
    "nt_state_blocked": {"tk": "🚫 Sen meni bloklapsyň. Açmak üçin aşakdaky düwmä bas.",
                         "ru": "🚫 Ты меня заблокировал. Нажми кнопку ниже, чтобы включить.",
                         "tr": "🚫 Beni engellemişsin. Açmak için aşağıdaki düğmeye bas."},
    "nt_today": {"tk": "Bu gün iberilen", "ru": "Отправлено сегодня", "tr": "Bugün gönderilen"},
    "nt_types": {"tk": "Näme barada ýazýaryn", "ru": "О чём напоминаю",
                 "tr": "Ne hakkında yazarım"},
    "nt_limits": {"tk": "ℹ️ Günde iň köp {max} habar, aralygy {gap} sagat. "
                        "Gije {start}:00–{end}:00 arasy asla ýazmaryn.",
                  "ru": "ℹ️ Не более {max} сообщений в день, минимум {gap} ч между ними. "
                        "Ночью с {start}:00 до {end}:00 не пишу.",
                  "tr": "ℹ️ Günde en fazla {max} mesaj, aralarında en az {gap} saat. "
                        "Gece {start}:00–{end}:00 arası hiç yazmam."},
    "nt_turned_on": {"tk": "🔔 Habarnamalar açyldy.", "ru": "🔔 Уведомления включены.",
                     "tr": "🔔 Bildirimler açıldı."},
    "nt_turned_off": {"tk": "🔕 Habarnamalar öçürildi. Islän wagtyň açyp bilersiň.",
                      "ru": "🔕 Уведомления выключены. Можешь включить в любой момент.",
                      "tr": "🔕 Bildirimler kapatıldı. İstediğin zaman açabilirsin."},
    "nt_b_on": {"tk": "🔔 Aç", "ru": "🔔 Включить", "tr": "🔔 Aç"},
    "nt_b_off": {"tk": "🔕 Habarnamalary öçür", "ru": "🔕 Отключить уведомления",
                 "tr": "🔕 Bildirimleri kapat"},
    # bildirim metinleri
    "nt_streak": {"tk": "🔥 <b>{n} günlük yzygiderligiň ýitmek howpunda!</b>\n"
                        "Sowgadyňy alsaň yzygiderligiň dowam eder.",
                  "ru": "🔥 <b>Твоя серия из {n} дней вот-вот прервётся!</b>\n"
                        "Забери подарок — и серия продолжится.",
                  "tr": "🔥 <b>{n} günlük serin bozulmak üzere!</b>\n"
                        "Hediyeni alırsan serin devam eder."},
    "nt_daily": {"tk": "🎁 Gündelik sowgadyň taýýar — alaýda!",
                 "ru": "🎁 Твой ежедневный подарок готов — забирай!",
                 "tr": "🎁 Günlük hediyen hazır — alsana!"},
    "nt_back3": {"tk": "👋 Seni küýsedik! Gaýdyp gelseň {coins} 🪙 + {gems} 💎 sowgat.",
                 "ru": "👋 Мы соскучились! Вернись и получи {coins} 🪙 + {gems} 💎.",
                 "tr": "👋 Seni özledik! Geri dönersen {coins} 🪙 + {gems} 💎 hediye."},
    "nt_back7": {"tk": "🎉 Bir hepde bäri ýoksuň! Uly gaýdyp geliş sowgady garaşýar: "
                       "{coins} 🪙 + {gems} 💎 + doly energiýa.",
                 "ru": "🎉 Тебя не было неделю! Ждёт большой подарок за возвращение: "
                       "{coins} 🪙 + {gems} 💎 + полная энергия.",
                 "tr": "🎉 Bir haftadır yoksun! Büyük dönüş hediyen bekliyor: "
                       "{coins} 🪙 + {gems} 💎 + dolu enerji."},
    "nt_boss": {"tk": "🐉 Täze aždarha peýda boldy! Urgy salyp paýyňy al.",
                "ru": "🐉 Появился новый босс! Ударь и забери свою долю.",
                "tr": "🐉 Yeni canavar doğdu! Vur ve payını al."},
    "nt_biz": {"tk": "🏭 Iş ýeriňiň kassasy doldy — ýygnamagyň wagty.",
               "ru": "🏭 Касса твоего бизнеса полна — пора собирать.",
               "tr": "🏭 İşletmenin kasası doldu — toplama zamanı."},
    "nt_energy": {"tk": "⚡ Energiýaň doldy! Oýnamaga taýýar.",
                  "ru": "⚡ Энергия восстановилась! Можно играть.",
                  "tr": "⚡ Enerjin doldu! Oynamaya hazırsın."},
    "nt_b_streak": {"tk": "🔥 Yzygiderligiňi halas et", "ru": "🔥 Спасти серию",
                    "tr": "🔥 Serini kurtar"},
    "nt_b_daily": {"tk": "🎁 Sowgadyňy al", "ru": "🎁 Забрать подарок", "tr": "🎁 Hediyeni al"},
    "nt_b_back": {"tk": "🎁 Sowgady al", "ru": "🎁 Забрать подарок", "tr": "🎁 Hediyeyi al"},
    "nt_b_boss": {"tk": "🐉 Urgy sal", "ru": "🐉 Атаковать", "tr": "🐉 Saldır"},
    "nt_b_biz": {"tk": "🏭 Ýygna", "ru": "🏭 Собрать", "tr": "🏭 Topla"},
    "nt_b_energy": {"tk": "🎮 Oýna", "ru": "🎮 Играть", "tr": "🎮 Oyna"},
    "nt_gift_ok": {"tk": "🎁 Hoş geldiň! {coins} 🪙 + {gems} 💎 hasabyňa geçdi.",
                   "ru": "🎁 С возвращением! {coins} 🪙 + {gems} 💎 зачислены.",
                   "tr": "🎁 Hoş geldin! {coins} 🪙 + {gems} 💎 hesabına geçti."},
    "nt_gift_none": {"tk": "Häzir garaşýan sowgat ýok.", "ru": "Сейчас подарка нет.",
                     "tr": "Şu an bekleyen hediye yok."},
    "nt_gift_late": {"tk": "⏰ Sowgadyň möhleti geçdi (48 sagat).",
                     "ru": "⏰ Срок подарка истёк (48 часов).",
                     "tr": "⏰ Hediyenin süresi doldu (48 saat)."},
    # ayar ekranındaki tür listesi
    "nt_type_streak": {"tk": "Yzygiderligiň ýitmek howpunda", "ru": "Серия под угрозой",
                       "tr": "Serin bozulmak üzere"},
    "nt_type_daily": {"tk": "Gündelik sowgat taýýar", "ru": "Ежедневный подарок готов",
                      "tr": "Günlük hediye hazır"},
    "nt_type_back7": {"tk": "Uzak wagt ýok bolsaň", "ru": "Если долго не заходишь",
                      "tr": "Uzun süre yoksan"},
    "nt_type_back3": {"tk": "Birnäçe gün ýok bolsaň", "ru": "Если пару дней не заходишь",
                      "tr": "Birkaç gün yoksan"},
    "nt_type_boss": {"tk": "Täze aždarha peýda bolanda", "ru": "Когда появляется босс",
                     "tr": "Yeni canavar doğunca"},
    "nt_type_miner": {"tk": "Magdançy kassasy dolanda", "ru": "Когда касса шахтёров полна",
                      "tr": "Madenci kasası dolunca"},
    "nt_type_biz": {"tk": "Iş ýeri kassasy dolanda", "ru": "Когда касса бизнеса полна",
                    "tr": "İşletme kasası dolunca"},
    "nt_type_energy": {"tk": "Energiýaň dolanda", "ru": "Когда энергия восстановилась",
                       "tr": "Enerjin dolunca"},
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
    keys = ["b_play", "b_money", "b_gift", "b_shop", "b_items", "b_friends", "b_menu",
            "b_support"]
    out = {}
    for key in keys:
        for lang in LANGS:
            out[t(lang, key)] = key
    return out

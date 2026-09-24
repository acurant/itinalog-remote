//! АйТиНалоги: режим сервера по умолчанию и переключатель
//! «сервер АйТиНалоги» / «публичные серверы RustDesk».
//!
//! Файл генерируется скриптом itinalog/apply_branding.py из brand.json —
//! правьте brand.json, а не этот файл.

use hbb_common::config::Config;

/// Ключ опции, в которой хранится выбранный режим.
pub const MODE_KEY: &str = "itinalog-server-mode";
/// Работа через сервер компании.
pub const MODE_OUR: &str = "itinalog";
/// Работа через публичные серверы RustDesk (как в оригинальной программе).
pub const MODE_PUBLIC: &str = "public";

pub const ID_SERVER: &str = "@@ID_SERVER@@";
pub const RELAY_SERVER: &str = "@@RELAY_SERVER@@";
pub const API_SERVER: &str = "@@API_SERVER@@";
pub const KEY: &str = "@@KEY@@";

const SERVER_OPTIONS: [&str; 4] = ["custom-rendezvous-server", "relay-server", "api-server", "key"];

fn our_values() -> [&'static str; 4] {
    [ID_SERVER, RELAY_SERVER, API_SERVER, KEY]
}

/// Текущий режим. Пустое значение (первый запуск) трактуется как режим сервера компании.
pub fn get_mode() -> String {
    let m = Config::get_option(MODE_KEY);
    if m == MODE_PUBLIC {
        MODE_PUBLIC.to_owned()
    } else {
        MODE_OUR.to_owned()
    }
}

/// Вызывается при старте каждого процесса (desktop, служба, Android/iOS).
/// В режиме сервера компании принудительно выставляет наши адреса и ключ,
/// в публичном режиме ничего не трогает (адреса пустые → встроенные серверы RustDesk).
pub fn init() {
    if Config::get_option(MODE_KEY).is_empty() {
        Config::set_option(MODE_KEY.to_owned(), MODE_OUR.to_owned());
    }
    if get_mode() == MODE_OUR {
        for (k, v) in SERVER_OPTIONS.iter().zip(our_values().iter()) {
            if Config::get_option(k) != *v {
                Config::set_option((*k).to_owned(), (*v).to_owned());
            }
        }
    }
}

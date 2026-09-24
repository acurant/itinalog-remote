// АйТиНалоги: переключатель «Сервер АйТиНалоги» / «Публичные серверы RustDesk».
import 'package:flutter/material.dart';
import 'package:flutter_hbb/common.dart';
import 'package:flutter_hbb/models/platform_model.dart';
import 'package:get/get.dart';

import 'brand.dart';

const String kItinalogModeKey = 'itinalog-server-mode';
const String kItinalogModeOur = 'itinalog';
const String kItinalogModePublic = 'public';

bool get _ru => localeName.toLowerCase().startsWith('ru');
String _t(String ru, String en) => _ru ? ru : en;

String itinalogModeTitle() => _t('Сервер подключения', 'Connection server');
String itinalogModeLabel(String mode) => mode == kItinalogModePublic
    ? _t('Публичные серверы RustDesk', 'Public RustDesk servers')
    : _t('Сервер $kBrandCompany', '$kBrandCompany server');
String itinalogModeHint(String mode) => mode == kItinalogModePublic
    ? _t('Напрямую через бесплатные серверы RustDesk',
        'Directly via free RustDesk servers')
    : kBrandIdServer;

Future<String> itinalogGetMode() async {
  final v = await bind.mainGetOption(key: kItinalogModeKey);
  return v == kItinalogModePublic ? kItinalogModePublic : kItinalogModeOur;
}

/// Переключает режим и сразу применяет адреса ID/Relay/API сервера и ключ.
Future<void> itinalogSetMode(String mode) async {
  await bind.mainSetOption(key: kItinalogModeKey, value: mode);
  if (mode == kItinalogModePublic) {
    // Пустые значения = встроенные публичные серверы RustDesk.
    await setServerConfig(null, null, ServerConfig());
  } else {
    await setServerConfig(
        null,
        null,
        ServerConfig(
            idServer: kBrandIdServer,
            relayServer: kBrandRelayServer,
            apiServer: kBrandApiServer,
            key: kBrandKey));
  }
}

/// Компактный переключатель (главный экран, мобильные настройки).
class ItinalogServerModeSwitch extends StatefulWidget {
  final bool enabled;
  final bool showTitle;
  /// Компактный вид (узкая левая панель главного экрана): без подписей.
  final bool compact;
  const ItinalogServerModeSwitch(
      {Key? key, this.enabled = true, this.showTitle = true, this.compact = false})
      : super(key: key);

  @override
  State<ItinalogServerModeSwitch> createState() =>
      _ItinalogServerModeSwitchState();
}

class _ItinalogServerModeSwitchState extends State<ItinalogServerModeSwitch> {
  String? _mode;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    itinalogGetMode().then((m) {
      if (mounted) setState(() => _mode = m);
    });
  }

  Future<void> _set(String mode) async {
    if (_busy || mode == _mode) return;
    setState(() => _busy = true);
    try {
      await itinalogSetMode(mode);
      _mode = mode;
      showToast(itinalogModeLabel(mode));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _option(String mode) {
    final selected = _mode == mode;
    return RadioListTile<String>(
      dense: true,
      contentPadding: EdgeInsets.zero,
      visualDensity: VisualDensity.compact,
      activeColor: kBrandPrimary,
      value: mode,
      groupValue: _mode,
      onChanged: (!widget.enabled || _busy)
          ? null
          : (v) {
              if (v != null) _set(v);
            },
      title: Text(itinalogModeLabel(mode),
          style: TextStyle(
              fontSize: 13,
              fontWeight: selected ? FontWeight.w600 : FontWeight.normal)),
      subtitle: widget.compact
          ? null
          : Text(itinalogModeHint(mode),
              style: const TextStyle(fontSize: 11),
              overflow: TextOverflow.ellipsis),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_mode == null) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (widget.showTitle)
          Row(children: [
            Icon(Icons.dns_outlined, size: 16, color: kBrandPrimary),
            const SizedBox(width: 6),
            Text(itinalogModeTitle(),
                style:
                    const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
          ]).marginOnly(bottom: 2),
        _option(kItinalogModeOur),
        _option(kItinalogModePublic),
      ],
    );
  }
}

/// Карточка для вкладки «Сеть» в настройках desktop-версии.
class ItinalogServerModeCard extends StatelessWidget {
  final bool enabled;
  const ItinalogServerModeCard({Key? key, this.enabled = true})
      : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Row(children: [
      Flexible(
        child: SizedBox(
          width: 600,
          child: Card(
            child: ItinalogServerModeSwitch(enabled: enabled)
                .paddingSymmetric(horizontal: 16, vertical: 10),
          ).marginOnly(left: 16, top: 15),
        ),
      ),
    ]);
  }
}

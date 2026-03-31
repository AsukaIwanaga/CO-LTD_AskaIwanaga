# 天気確認（開発部）

Open-Meteo API で横浜の天気予報を取得します（無料・APIキー不要）。

## フロー

1. 以下のURLで天気データを取得する（WebFetch を使用）：
   ```
   https://api.open-meteo.com/v1/forecast?latitude=35.4437&longitude=139.6380&current=temperature_2m,weathercode,windspeed_10m&daily=temperature_2m_max,temperature_2m_min,weathercode,precipitation_sum&timezone=Asia%2FTokyo&forecast_days=7
   ```

2. WMO 天気コードを日本語に変換する：
   - 0: 快晴
   - 1,2,3: 晴れ/薄曇り/曇り
   - 45,48: 霧
   - 51,53,55: 霧雨
   - 61,63,65: 雨
   - 71,73,75: 雪
   - 80,81,82: にわか雨
   - 95: 雷雨

3. 以下のフォーマットで表示する：

```
🌤 天気予報 — 横浜
─────────────────────────
現在: XX°C / 快晴 💨 X m/s

7日間予報:
MM/DD(曜) 天気      最高  最低  降水
03/18(水) ☀ 快晴   22°  14°  0.0mm
03/19(木) ⛅ 曇り  18°  12°  2.5mm
03/20(金) 🌧 雨    15°  10°  8.0mm
```

## 天気アイコン対応
- 快晴: ☀
- 晴れ/薄曇り: 🌤
- 曇り: ⛅
- 霧: 🌫
- 雨: 🌧
- にわか雨: 🌦
- 雪: ❄
- 雷雨: ⛈

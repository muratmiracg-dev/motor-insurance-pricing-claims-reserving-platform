# Kasko Teknik Fiyatlama, Hasar ve Rezerv Analitiği Platformu

[English README](README.md)

<p align="center">
  <img src="powerbi/mockups/01_executive_performance.png" alt="Kasko teknik performans dashboard'u" width="100%">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Power%20BI-PBIP%20Ready-F2C811?logo=powerbi&logoColor=black" alt="Power BI">
  <img src="https://img.shields.io/badge/Test-13%20başarılı-2E7D62" alt="13 başarılı test">
  <img src="https://img.shields.io/badge/Veri-%25100%20sentetik-C5524A" alt="Sentetik veri">
</p>

Bu proje, kurgusal bir Türkiye kasko sigortacısının teknik kârlılık ve hasar
kararlarını desteklemek için hazırlanmış uçtan uca portföy çalışmasıdır. Hasar
frekansı, hasar şiddeti, saf prim, fiyat yeterliliği, loss ratio, Chain Ladder,
Bornhuetter-Ferguson ve insan kontrollü suistimal inceleme kuyruğunu aynı veri
modelinde birleştirir.

> Müşteri, poliçe, araç, hasar, ödeme, rezerv ve suistimal etiketlerinin tamamı
> sentetiktir. Çıktılar gerçek fiyatlama, underwriting, rezerv, hasar ödemesi veya
> olumsuz müşteri kararı için onaylı değildir.

## İş problemi

Hangi kasko segmentleri eksik fiyatlanıyor, hasar maliyetini hangi faktörler
artırıyor, ödenmemiş hasarlar için ne kadar yükümlülük izlenmeli ve hangi dosyalar
yetkili insan incelemesine öncelikli olarak yönlendirilmelidir?

## Doğrulanmış sonuçlar

Sonuçlar `20260902` tohumu ve `31.12.2025` değerleme tarihiyle yeniden üretilebilir.

| Gösterge | Sonuç |
| --- | ---: |
| Poliçe / maruziyet yılı | 60.000 / 51.365,60 |
| Hasar / ödeme kaydı | 8.542 / 14.570 |
| Kazanılmış prim | 1,230 milyar TL |
| Gerçekleşen hasar | 888,56 milyon TL |
| Hasar frekansı | %16,63 |
| Ortalama hasar şiddeti | 104.022,70 TL |
| Loss ratio / combined ratio | %72,23 / %103,08 |
| OOT frekans kalibrasyonu | 0,982 |
| OOT saf prim kalibrasyonu | 0,866 |
| Prim artışı incelemesine giren poliçe | %33,60 |
| Chain Ladder IBNR | 170,58 milyon TL |
| Bornhuetter-Ferguson IBNR | 53,28 milyon TL |
| İnsan inceleme kuyruğu | 439 hasar / %5,14 |
| İnceleme hassasiyeti / rastgeleye göre lift | %14,12 / 3,82 kat |
| Otomatik hasar reddi | 0 |

Chain Ladder'ın sentetik nihai hasara göre toplam hatası yalnızca `%0,01`'dir.
Bu sonuç, sabit ve deterministik sentetik gelişim deseninden kaynaklanan bir
yeniden üretilebilirlik ölçüsüdür; gerçek portföy rezerv doğruluğu iddiası değildir.
Bornhuetter-Ferguson karşılaştırma modeli nihai hasarı `%13,08` düşük tahmin ederek
beklenen loss ratio varsayımının riskini görünür kılar.

## Dashboard görsel turu

<table>
  <tr>
    <td width="50%"><strong>1. Yönetici Teknik Performansı</strong><br><img src="powerbi/mockups/01_executive_performance.png" alt="Yönetici teknik performansı"></td>
    <td width="50%"><strong>2. Frekans ve Şiddet</strong><br><img src="powerbi/mockups/02_frequency_severity.png" alt="Frekans ve şiddet analizi"></td>
  </tr>
  <tr>
    <td width="50%"><strong>3. Fiyat Yeterliliği</strong><br><img src="powerbi/mockups/03_pricing_adequacy.png" alt="Fiyat yeterliliği"></td>
    <td width="50%"><strong>4. Hasar Operasyonları</strong><br><img src="powerbi/mockups/04_claims_operations.png" alt="Hasar operasyonları"></td>
  </tr>
  <tr>
    <td width="50%"><strong>5. Rezerv ve IBNR</strong><br><img src="powerbi/mockups/05_reserving_ibnr.png" alt="Rezerv ve IBNR"></td>
    <td width="50%"><strong>6. İnsan İncelemesi ve Yönetişim</strong><br><img src="powerbi/mockups/06_human_review_governance.png" alt="İnsan incelemesi ve yönetişim"></td>
  </tr>
</table>

## Analitik kapsam

- Yazılan/kazanılmış prim, ödenen hasar, muallak rezerv ve gerçekleşen hasar
- Frekans, şiddet, loss ratio, combined ratio ve açık dosya oranı
- Exposure ağırlıklı Poisson GLM frekans modeli
- Pozitif hasar tutarları için Gamma GLM şiddet modeli
- Saf prim ve masraf/komisyon düzeltilmiş teknik prim
- Fiyat yeterlilik endeksi ve tarife inceleme grupları
- Üçgensel hasar gelişimi, Chain Ladder ve Bornhuetter-Ferguson
- Açıklanabilir reason code'lu, insan kontrollü suistimal önceliklendirmesi
- Python, PostgreSQL, Excel ve Power BI çıktıları

## Projeyi çalıştırma

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
PYTHONPATH=src python scripts/run_pipeline.py
PYTHONPATH=src python -m unittest discover -s tests -v
```

Hızlı geliştirme çalıştırması:

```bash
PYTHONPATH=src python scripts/run_pipeline.py --n-policies 6000
```

## Başlıca teslimatlar

- `artifacts/run_manifest.json`: doğrulanmış sonuç ve çalıştırma kimliği
- `artifacts/pricing/`: fiyatlama skorları, ölçümler ve GLM katsayıları
- `artifacts/reserving/`: gelişim üçgenleri, faktörler ve rezerv sonuçları
- `artifacts/fraud/`: insan inceleme kuyruğu ve performans ölçümleri
- `reports/motor_insurance_analytics_workbench.xlsx`: çok sayfalı Excel çalışma kitabı
- `powerbi/measures.dax`: ortak KPI ölçü katmanı
- `powerbi/DASHBOARD_SPEC.md`: altı karar odaklı rapor sayfası sözleşmesi
- `powerbi/mockups/`: altı adet 16:9 dashboard ön izlemesi
- `sql/schema.sql`: PostgreSQL analitik veri modeli

## Power BI portföy raporu

Paket; Yönetici Teknik Performans, Frekans ve Şiddet, Fiyat Yeterliliği, Hasar
Operasyonları, Rezerv ve IBNR ile İnsan İnceleme ve Yönetişim sayfalarını içerir.
Veri martlarını ve ön izlemeleri üretmek için:

```bash
python scripts/build_powerbi_assets.py
```

Ardından Power BI Desktop içinde `powerbi/README.md` adımlarını izleyin. Proje;
kontrollü veri girdilerini, ilişki sözleşmesini, DAX ölçülerini, temayı ve sayfa
tasarımını sağlar. Üretilen PBIP/PBIR/TMDL metadata'sını Desktop doğrular.

## Yönetim sınırı

Projede korunan özellikler kullanılmaz. Fraud skoru yalnızca dosya inceleme
önceliği oluşturur; otomatik ret veya ödeme azaltımı üretemez. Fiyatlama ve rezerv
sonuçları ancak aktüerya, hukuk, uyum ve model risk onayı sonrasında gerçek süreçte
değerlendirilebilir.

Detaylar için [proje sözleşmesi](docs/PROJECT_CHARTER.md),
[veri sözlüğü](docs/DATA_DICTIONARY.md) ve
[model yönetişimi](docs/MODEL_GOVERNANCE.md) belgelerine bakılabilir.

## Kaynak uyumu

Sektör bağlamı için [TSB motor istatistikleri](https://www.tsb.org.tr/tr/istatistik/motorlu-tasitlar-istatistikleri),
[SBM](https://www.sbm.org.tr/) ve SEDDK'nin
[2026/27 sayılı genelgesi](https://www.seddk.gov.tr/UploadContent/Documents/2026-27%20say%C4%B1l%C4%B1%20Genelge.pdf)
kullanılmıştır. Hiçbir gerçek sigortalı veya şirket kaydı kullanılmamıştır.

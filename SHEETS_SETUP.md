# Google Sheets Integration Setup

## ধাপ ১: Google Cloud Console Setup

1. [Google Cloud Console](https://console.cloud.google.com/) এ যান
2. নতুন Project তৈরি করুন (অথবা existing project select করুন)
3. **APIs & Services > Library** এ যান
4. "Google Sheets API" search করে **Enable** করুন
5. **APIs & Services > Credentials** এ যান
6. **Create Credentials > Service Account** select করুন
7. Service account name দিন (যেমন: ngo-sheets-sync)
8. **Create and Continue** click করুন
9. Role select করুন: **Editor**
10. **Done** click করুন

## ধাপ ২: Service Account Key Download

1. **Service Accounts** list থেকে আপনার service account select করুন
2. **Keys** tab এ যান
3. **Add Key > Create New Key** click করুন
4. **JSON** select করে **Create** click করুন
5. JSON file download হবে - এটার নাম `credentials.json` করুন
6. এই file টি আপনার project root folder এ রাখুন (যেখানে app.py আছে)

## ধাপ ৩: Google Sheet তৈরি করুন

1. [Google Sheets](https://sheets.google.com) এ যান
2. নতুন spreadsheet তৈরি করুন
3. নাম দিন: **NGO Management**
4. নিচের sheets তৈরি করুন (exact নাম):
   - `Customers`
   - `Loans`
   - `Loan Collections`
   - `Saving Collections`

## ধাপ ৪: Sheet এ Access দিন

1. `credentials.json` file open করুন
2. `client_email` field এর value copy করুন (যেমন: ngo-sheets-sync@project.iam.gserviceaccount.com)
3. আপনার Google Sheet এ **Share** button click করুন
4. Service account email paste করুন
5. **Editor** permission দিন
6. **Send** click করুন

## ধাপ ৫: Dependencies Install

```bash
pip install -r requirements.txt
```

## ধাপ ৬: Application Run করুন

```bash
python app.py
```

## কিভাবে কাজ করে?

- যখন নতুন **Customer** যোগ হবে → Google Sheets এ auto sync হবে
- যখন নতুন **Loan** দেওয়া হবে → Google Sheets এ auto sync হবে
- যখন **Loan Collection** হবে → Google Sheets এ auto sync হবে
- যখন **Saving Collection** হবে → Google Sheets এ auto sync হবে

## Troubleshooting

### যদি credentials.json না থাকে:
- Application চলবে কিন্তু Google Sheets sync হবে না
- শুধু SQLite database এ data save হবে

### যদি Sheet access না থাকে:
- Service account email কে Sheet এ Editor access দিতে হবে

### যদি Sheet name ভুল হয়:
- Sheet এর নাম exactly এই রকম হতে হবে:
  - Customers
  - Loans
  - Loan Collections
  - Saving Collections

## সুবিধা

✅ **Real-time Backup** - সব data Google Sheets এ automatically backup হয়
✅ **Easy Access** - যেকোনো জায়গা থেকে Google Sheets দেখা যায়
✅ **Excel Export** - Google Sheets থেকে সহজেই Excel এ download করা যায়
✅ **No Extra Cost** - সম্পূর্ণ Free
✅ **Collaboration** - Multiple users একসাথে দেখতে পারবে

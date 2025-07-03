# วิธีการ Deploy โปรเจค Facebook Reels Downloader ไปยัง Firebase

## เตรียมความพร้อม

### 1. สร้าง Firebase Project
1. ไปที่ [Firebase Console](https://console.firebase.google.com/)
2. คลิก "Add project" หรือ "เพิ่มโปรเจค"
3. ตั้งชื่อโปรเจค (เช่น `facebook-reels-downloader`)
4. เปิดใช้งาน Google Analytics (ตามต้องการ)
5. สร้างโปรเจค

### 2. เปิดใช้งาน Services ที่จำเป็น
ใน Firebase Console:
1. ไปที่ **Hosting** -> คลิก "Get started"
2. ไปที่ **Functions** -> คลิก "Get started"

## การติดตั้งและ Deploy

### 1. ติดตั้ง Firebase CLI
```bash
npm install -g firebase-tools
```

### 2. Login เข้า Firebase
```bash
firebase login
```

### 3. กำหนด Project ID
แก้ไขไฟล์ `.firebaserc` และเปลี่ยน `your-firebase-project-id` เป็น Project ID ของคุณ:
```json
{
  "projects": {
    "default": "your-actual-project-id"
  }
}
```

### 4. Deploy โปรเจค
```bash
firebase deploy
```

## การตั้งค่า Environment Variables (ถ้าต้องการ)

ถ้าคุณต้องการใช้ Facebook cookies สำหรับดาวน์โหลด private videos:

```bash
firebase functions:config:set facebook.cookie="your-facebook-cookie-string"
```

## URL ที่ได้หลังจาก Deploy

หลังจาก deploy สำเร็จ คุณจะได้:
- **Hosting URL**: `https://your-project-id.web.app`
- **Function URL**: `https://your-region-your-project-id.cloudfunctions.net/app`

## โครงสร้างไฟล์

```
Download/
├── firebase.json          # Firebase configuration
├── .firebaserc           # Firebase project settings
├── public/              
│   └── index.html        # Static web files
├── functions/
│   ├── main.py          # Cloud Function code
│   └── requirements.txt  # Python dependencies
└── FIREBASE_DEPLOY.md   # คู่มือนี้
```

## การแก้ปัญหา

### ปัญหา: Function timeout
ถ้าการดาวน์โหลดใช้เวลานาน ให้เพิ่ม timeout ใน `firebase.json`:
```json
{
  "functions": {
    "source": "functions",
    "runtime": "python311",
    "timeout": "540s"
  }
}
```

### ปัญหา: Memory limit
สำหรับไฟล์ขนาดใหญ่ ให้เพิ่ม memory ใน function:
```json
{
  "functions": {
    "source": "functions",
    "runtime": "python311",
    "memory": "1GB"
  }
}
```

## ข้อจำกัดของ Firebase Functions

- **Timeout**: สูงสุด 9 นาที
- **Memory**: สูงสุด 8GB
- **File size**: จำกัดด้วย memory ที่ตั้งค่า
- **Cold start**: Function อาจช้าในการเริ่มต้นครั้งแรก

## คำสั่งที่มีประโยชน์

```bash
# ดู logs
firebase functions:log

# Test local
firebase emulators:start

# Update เฉพาะ functions
firebase deploy --only functions

# Update เฉพาะ hosting
firebase deploy --only hosting
``` 
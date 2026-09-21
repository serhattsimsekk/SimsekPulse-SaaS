$ErrorActionPreference = "Continue"
$IP = "207.154.217.198"

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "SimsekLog OS v5.0 - DigitalOcean Canliya Alma Sihirbazi" -ForegroundColor Green
Write-Host "Hedef Sunucu: $IP (simseklog.com)" -ForegroundColor Yellow
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "DIKKAT: Sifrenizi yazarken ekranda karakterler veya yildiz gorunmez." -ForegroundColor Yellow
Write-Host "Lutfen sifrenizi tuslayip dogrudan ENTER tusuna basiniz." -ForegroundColor Yellow
Write-Host ""

Write-Host "[1/3] Sunucuda /var/www/simseklog dizini olusturuluyor..." -ForegroundColor Cyan
ssh -o StrictHostKeyChecking=no root@$IP "mkdir -p /var/www/simseklog"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Sunucu baglantisinda hata olustu veya sifre yanlis girildi." -ForegroundColor Red
    Write-Host "Lutfen sifrenizi kontrol edip tekrar deneyiniz." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Pencereyi kapatmak icin ENTER tusuna basiniz"
    exit
}

Write-Host ""
Write-Host "[2/3] Proje dosyalari sunucuya yukleniyor (SCP)..." -ForegroundColor Cyan
scp -o StrictHostKeyChecking=no -r utils modules data ./* "root@${IP}:/var/www/simseklog/"
Write-Host ""
Write-Host "[3/3] Sunucuda kurulum ve SSL sertifikasi ayarlaniyor..." -ForegroundColor Cyan
ssh -t -o StrictHostKeyChecking=no root@$IP "cd /var/www/simseklog && sed -i 's/\r$//' deploy.sh && chmod +x deploy.sh && ./deploy.sh"

Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "TEBRIKLER! SimsekLog OS v5.0 canliya alindi!" -ForegroundColor Green
Write-Host "Adres: https://www.simseklog.com" -ForegroundColor Yellow
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Read-Host "Pencereyi kapatmak icin ENTER tusuna basiniz"

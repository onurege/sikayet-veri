from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": ["Content-Type"]}})

@app.route('/api/search', methods=['GET'])
def search_complaints():
    Şikayet Verileri
    
    keyword = request.args.get('q', '')
    fetch_all = request.args.get('all', 'true').lower() == 'true'
    search_type = request.args.get('type', 'company')
    
    if not keyword:
        return jsonify({'error': 'Anahtar kelime gerekli'}), 400
    
    all_complaints = []
    page = 1
    max_pages = 100
    total_pages_found = False
    consecutive_empty_pages = 0
    
    try:
        while page <= max_pages:
            print(f"\n🔄 Sayfa {page} çekiliyor...")
            
            # URL formatı
            if search_type == 'keyword' or '/' in keyword or ' ' in keyword:
                if page == 1:
                    url = f'https://www.sikayetvar.com/sikayetler?k={keyword}'
                else:
                    url = f'https://www.sikayetvar.com/sikayetler?k={keyword}&sayfa={page}'
            else:
                if page == 1:
                    url = f'https://www.sikayetvar.com/{keyword}'
                else:
                    url = f'https://www.sikayetvar.com/{keyword}?page={page}'
            
            print(f"📍 URL: {url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'tr-TR,tr;q=0.9',
                'Connection': 'keep-alive',
                'Referer': f'https://www.sikayetvar.com/{keyword}'
            }
            
            session = requests.Session()
            response = session.get(url, headers=headers, timeout=15, allow_redirects=True)
            response.raise_for_status()
            
            # Yönlendirme kontrolü
            final_url = response.url
            expected_url = url.rstrip('/')
            actual_url = final_url.rstrip('/')
            
            if actual_url != expected_url:
                print(f"⚠️ Sayfa {page} farklı URL'ye yönlendirildi:")
                print(f"   İstenilen: {expected_url}")
                print(f"   Gelen: {actual_url}")
                
                if page > 1 and '/sikayetler' in actual_url and '?k=' in actual_url:
                    if 'sayfa=' not in actual_url and 'page=' not in actual_url:
                        print(f"✅ Son sayfaya ulaşıldı (ilk sayfaya yönlendirildi)")
                        break
                
                if page > 1 and actual_url == f'https://www.sikayetvar.com/{keyword}':
                    print(f"✅ Son sayfaya ulaşıldı (ana sayfaya yönlendirildi)")
                    break
            
            if response.encoding is None or response.encoding == 'ISO-8859-1':
                response.encoding = 'utf-8'
            
            html = response.text
            
            if 'Ã' in html[:1000]:
                try:
                    html = response.content.decode('utf-8')
                except:
                    pass
            
            soup = BeautifulSoup(html, 'html.parser')
            
            complaint_cards = soup.find_all('article', class_='card-v2')
            
            if not complaint_cards:
                consecutive_empty_pages += 1
                print(f"⚠️ Sayfa {page}'de şikayet kartı bulunamadı (Arka arkaya boş: {consecutive_empty_pages})")
                
                if consecutive_empty_pages >= 2:
                    print(f"✅ 2 sayfa üst üste boş, aramayı sonlandırılıyor")
                    break
                
                page += 1
                import random
                wait_time = random.uniform(2, 4)
                print(f"⏳ {wait_time:.1f} saniye bekleniyor...")
                time.sleep(wait_time)
                continue
            
            print(f"✅ Sayfa {page}'de {len(complaint_cards)} kart bulundu")
            
            # Debug için ilk 5 kartı kaydet
            if page == 1 and len(all_complaints) == 0:
                for i in range(min(5, len(complaint_cards))):
                    with open(f'debug_card_{i+1}.html', 'w', encoding='utf-8') as f:
                        f.write(str(complaint_cards[i].prettify()))
                print(f"  📝 İlk {min(5, len(complaint_cards))} kart debug dosyalarına kaydedildi")
            
            page_complaints = []
            failed_cards = 0
            
            for idx, card in enumerate(complaint_cards):
                try:
                    if idx < 5 and page == 1:
                        card_id = card.get('data-id', 'unknown')
                        print(f"    🔍 === KART #{idx+1} (ID: {card_id}) ===")
                    
                    # BAŞLIK
                    title = None
                    link = ''
                    
                    title_link = card.find('a', class_='complaint-description')
                    if not title_link:
                        title_link = card.find('a', class_='complaint-layer')
                    
                    if not title_link:
                        div_layer = card.find('div', class_='complaint-layer')
                        if div_layer:
                            title = div_layer.get_text(strip=True)
                            link = div_layer.get('data-complaint-link', '')
                            title_link = True
                    
                    if not title_link:
                        h2 = card.find('h2', class_='complaint-title')
                        if h2:
                            title_link = h2.find('a')
                            if not title_link:
                                div_layer = h2.find('div', class_='complaint-layer')
                                if div_layer:
                                    title = div_layer.get_text(strip=True)
                                    link = div_layer.get('data-complaint-link', '')
                                    title_link = True
                    
                    if title_link and isinstance(title_link, bool) == False:
                        title = title_link.get_text(strip=True)
                        link = title_link.get('href', '')
                    
                    if idx < 5 and page == 1:
                        if title:
                            print(f"       ✅ Başlık: '{title[:50]}'...")
                        else:
                            print(f"       ❌ Başlık bulunamadı")
                    
                    if not title or len(title) < 5:
                        failed_cards += 1
                        continue
                    
                    if link and not link.startswith('http'):
                        link = 'https://www.sikayetvar.com' + link
                    
                    # ŞİRKET
                    company = 'Bilinmiyor'
                    company_elem = (
                        card.find('a', class_=lambda x: x and any(w in str(x).lower() for w in ['brand', 'company', 'firma'])) or
                        card.find('span', class_=lambda x: x and any(w in str(x).lower() for w in ['brand', 'company', 'firma']))
                    )
                    if company_elem:
                        company = company_elem.get_text(strip=True)
                    
                    # İÇERİK
                    content = ''
                    
                    desc_elem = card.find('p', class_=lambda x: x and 'complaint-description' in str(x))
                    
                    if idx < 5 and page == 1:
                        if desc_elem:
                            print(f"       ✅ p.complaint-description bulundu")
                        else:
                            print(f"       ⚠️  p.complaint-description YOK")
                    
                    if not desc_elem:
                        desc_elem = card.find('a', class_=lambda x: x and 'complaint-description' in str(x))
                        if idx < 5 and page == 1 and desc_elem:
                            print(f"       ⚠️  a.complaint-description bulundu")
                    
                    if desc_elem:
                        content = desc_elem.get_text(strip=True)
                        content = content.replace('...', '').strip()
                        
                        if idx < 5 and page == 1:
                            print(f"       📝 İçerik: '{content[:80]}'...")
                        
                        if content.startswith('+') and len(content) <= 3:
                            if idx < 5 and page == 1:
                                print(f"       ❌ Görsel sayısı '{content}', atlanıyor")
                            content = ''
                        
                        if content and len(content) < 20:
                            if idx < 5 and page == 1:
                                print(f"       ❌ Çok kısa ({len(content)} kar), atlanıyor")
                            content = ''
                    
                    if not content:
                        all_paragraphs = card.find_all('p')
                        texts = []
                        for p in all_paragraphs:
                            p_text = p.get_text(strip=True)
                            if p_text and len(p_text) > 20 and not p_text.startswith('+'):
                                texts.append(p_text)
                        if texts:
                            content = ' '.join(texts)
                    
                    if not content:
                        detail_elem = card.find('div', class_='complaint-detail')
                        if detail_elem:
                            content = detail_elem.get_text(strip=True)
                    
                    if content:
                        content = ' '.join(content.split())
                    else:
                        if card.find('video') or card.find('div', class_='complaint-attachments'):
                            content = '[Video/Fotoğraf şikayeti - metin yok]'
                        else:
                            content = ''
                    
                    # UPVOTE
                    upvotes = 0
                    upvote_attr = card.get('data-upvoter-count', '0')
                    try:
                        upvotes = int(upvote_attr)
                    except:
                        pass
                    
                    complaint_id = card.get('data-id', '')
                    
                    # DURUM
                    status = 'Beklemede'
                    solved_badge = card.find('div', class_='solved-badge')
                    if solved_badge:
                        badge_text = solved_badge.get_text(strip=True).lower()
                        if 'çözüldü' in badge_text:
                            status = 'Çözüldü'
                        else:
                            status = solved_badge.get_text(strip=True)
                    else:
                        status_elem = card.find('div', class_=lambda x: x and 'status' in str(x).lower())
                        if status_elem:
                            status_text = status_elem.get_text(strip=True).lower()
                            if 'çözüldü' in status_text or 'çözüldi' in status_text:
                                status = 'Çözüldü'
                            elif 'cevaplandı' in status_text:
                                status = 'Cevaplandı'
                    
                    # TARİH
                    date = ''
                    date_elem = (
                        card.find('time') or
                        card.find('span', class_=lambda x: x and 'date' in str(x).lower()) or
                        card.find('div', class_=lambda x: x and 'date' in str(x).lower())
                    )
                    if date_elem:
                        date = date_elem.get_text(strip=True)
                    
                    page_complaints.append({
                        'id': len(all_complaints) + len(page_complaints) + 1,
                        'complaint_id': complaint_id,
                        'title': title,
                        'content': content,
                        'company': company,
                        'date': date,
                        'link': link,
                        'upvotes': upvotes,
                        'status': status,
                        'page': page
                    })
                    
                except Exception as e:
                    failed_cards += 1
                    if page <= 2 and failed_cards <= 3:
                        print(f"  ✗ Kart #{idx+1} parse hatası: {e}")
                    continue
            
            if failed_cards > 0:
                print(f"  ⚠️  Toplam {failed_cards}/{len(complaint_cards)} kart parse edilemedi")
                print(f"  ✅ Başarıyla parse edilen: {len(page_complaints)} şikayet")
            
            all_complaints.extend(page_complaints)
            
            if len(page_complaints) == 0 and len(complaint_cards) > 0:
                consecutive_empty_pages += 1
                print(f"⚠️  {len(complaint_cards)} kart bulundu ama hiçbiri parse edilemedi (Arka arkaya: {consecutive_empty_pages})")
                
                if consecutive_empty_pages >= 2:
                    print(f"✅ 2 sayfa üst üste veri parse edilemedi, aramayı sonlandırıyorum")
                    break
            elif len(page_complaints) > 0:
                consecutive_empty_pages = 0
                print(f"📊 Toplam çekilen: {len(all_complaints)} şikayet")
            
            if not fetch_all:
                break
            
            if page == 1 and not total_pages_found:
                pagination = soup.find('ul', class_='pagination-list')
                if pagination:
                    all_page_items = pagination.find_all('li')
                    max_page_num = 0
                    
                    for item in all_page_items:
                        title = item.get('title', '')
                        if '/' in title:
                            parts = title.split('/')
                            if len(parts) >= 2:
                                try:
                                    page_total = parts[1].split('-')[0].strip()
                                    page_num = int(page_total)
                                    if page_num > max_page_num:
                                        max_page_num = page_num
                                except:
                                    pass
                        
                        href = item.get('href', '')
                        if 'page=' in href or 'sayfa=' in href:
                            try:
                                if 'page=' in href:
                                    page_num = int(href.split('page=')[1].split('&')[0])
                                else:
                                    page_num = int(href.split('sayfa=')[1].split('&')[0])
                                if page_num > max_page_num:
                                    max_page_num = page_num
                            except:
                                pass
                    
                    if max_page_num > 0:
                        max_pages = min(max_page_num, 100)
                        total_pages_found = True
                        print(f"📄 Toplam {max_page_num} sayfa tespit edildi (işlenecek: {max_pages})")
                    else:
                        print(f"⚠️  Pagination var ama sayfa sayısı tespit edilemedi, devam ediliyor...")
                else:
                    print(f"📄 Pagination elementi yok (tek sayfa olabilir, arka arkaya boş sayfa kontrolüyle devam)")
            
            if total_pages_found and page >= max_pages:
                print(f"✅ Toplam {max_pages} sayfa çekildi")
                break
            
            page += 1
            
            import random
            wait_time = random.uniform(2, 4)
            print(f"⏳ {wait_time:.1f} saniye bekleniyor...")
            time.sleep(wait_time)
        
        print(f"\n✅ Toplam {len(all_complaints)} şikayet {page} sayfadan çekildi\n")
        
        return jsonify({
            'success': True,
            'keyword': keyword,
            'count': len(all_complaints),
            'pages': page,
            'complaints': all_complaints,
            'scraped_at': datetime.now().isoformat()
        })
        
    except requests.RequestException as e:
        error_msg = str(e)
        print(f"❌ İstek hatası: {error_msg}")
        
        if '429' in error_msg:
            return jsonify({
                'error': 'Çok fazla istek! Sikayetvar.com geçici olarak engelledi. Lütfen birkaç dakika bekleyin.',
                'success': False,
                'partial_data': all_complaints if all_complaints else None,
                'pages_scraped': page - 1
            }), 429
        
        return jsonify({
            'error': f'İstek hatası: {error_msg}',
            'success': False,
            'partial_data': all_complaints if all_complaints else None,
            'pages_scraped': page - 1
        }), 500
    except Exception as e:
        print(f"❌ Beklenmeyen hata: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': f'Beklenmeyen hata: {str(e)}',
            'success': False
        }), 500

@app.route('/api/export/excel', methods=['POST', 'OPTIONS'])
def export_excel():
    """Şikayetleri Excel formatında indir"""
    
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response, 200
    
    try:
        data = request.json
        complaints = data.get('complaints', [])
        keyword = data.get('keyword', 'arama')
        
        if not complaints:
            return jsonify({'error': 'Veri bulunamadı'}), 400
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Şikayetler"
        
        headers = ['#', 'Şikayet ID', 'Başlık', 'Şirket', 'Durum', 'Upvote', 'Tarih', 'İçerik', 'Link']
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=12)
        
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        for row_num, complaint in enumerate(complaints, 2):
            ws.cell(row=row_num, column=1, value=complaint.get('id', row_num-1))
            ws.cell(row=row_num, column=2, value=complaint.get('complaint_id', ''))
            
            title_cell = ws.cell(row=row_num, column=3, value=complaint.get('title', ''))
            title_cell.font = Font(bold=True, size=11)
            title_cell.alignment = Alignment(wrap_text=True, vertical='top')
            
            company_cell = ws.cell(row=row_num, column=4, value=complaint.get('company', ''))
            company_cell.alignment = Alignment(horizontal='center', vertical='center')
            
            status = complaint.get('status', 'Beklemede')
            status_cell = ws.cell(row=row_num, column=5, value=status)
            status_cell.alignment = Alignment(horizontal='center', vertical='center')
            
            if status == 'Çözüldü':
                status_cell.fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
                status_cell.font = Font(color="006100", bold=True)
            elif status == 'Cevaplandı':
                status_cell.fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
                status_cell.font = Font(color="9C6500")
            
            upvote_cell = ws.cell(row=row_num, column=6, value=complaint.get('upvotes', 0))
            upvote_cell.alignment = Alignment(horizontal='center', vertical='center')
            
            date_cell = ws.cell(row=row_num, column=7, value=complaint.get('date', ''))
            date_cell.alignment = Alignment(horizontal='center', vertical='center')
            
            content_cell = ws.cell(row=row_num, column=8, value=complaint.get('content', ''))
            content_cell.alignment = Alignment(wrap_text=True, vertical='top')
            
            link = complaint.get('link', '')
            link_cell = ws.cell(row=row_num, column=9, value=link)
            if link:
                link_cell.hyperlink = link
                link_cell.font = Font(color="0563C1", underline="single")
            link_cell.alignment = Alignment(vertical='center')
        
        ws.column_dimensions['A'].width = 5
        ws.column_dimensions['B'].width = 12
        ws.column_dimensions['C'].width = 50
        ws.column_dimensions['D'].width = 20
        ws.column_dimensions['E'].width = 15
        ws.column_dimensions['F'].width = 10
        ws.column_dimensions['G'].width = 15
        ws.column_dimensions['H'].width = 70
        ws.column_dimensions['I'].width = 15
        
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        for row in ws.iter_rows(min_row=1, max_row=len(complaints)+1, min_col=1, max_col=9):
            for cell in row:
                cell.border = thin_border
        
        ws.freeze_panes = 'A2'
        
        summary_ws = wb.create_sheet(title="Özet")
        summary_ws['A1'] = 'Şikayetvar Rapor Özeti'
        summary_ws['A1'].font = Font(bold=True, size=16)
        
        summary_data = [
            ['Arama Kelimesi:', keyword],
            ['Toplam Şikayet:', len(complaints)],
            ['Rapor Tarihi:', datetime.now().strftime('%d.%m.%Y %H:%M')],
            ['', ''],
            ['Durum Dağılımı:', ''],
        ]
        
        status_count = {}
        for c in complaints:
            status = c.get('status', 'Beklemede')
            status_count[status] = status_count.get(status, 0) + 1
        
        for status, count in status_count.items():
            summary_data.append([f'  {status}:', count])
        
        for row_num, (label, value) in enumerate(summary_data, 1):
            summary_ws[f'A{row_num}'] = label
            summary_ws[f'B{row_num}'] = value
            summary_ws[f'A{row_num}'].font = Font(bold=True)
        
        summary_ws.column_dimensions['A'].width = 25
        summary_ws.column_dimensions['B'].width = 20
        
        excel_file = io.BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)
        
        filename = f'sikayetvar_{keyword}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"❌ Excel export hatası: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Excel oluşturma hatası: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """API sağlık kontrolü"""
    return jsonify({
        'status': 'healthy',
        'message': 'Şikayetvar Scraper API çalışıyor',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/')
def home():
    """Ana sayfa"""
    return '''
    <h1>Şikayetvar Scraper API</h1>
    <p>Kullanım: <code>/api/search?q=ANAHTAR_KELIME</code></p>
    <p>Örnek: <a href="/api/search?q=trendyol">/api/search?q=trendyol</a></p>
    <p>Sağlık: <a href="/api/health">/api/health</a></p>
    '''

if __name__ == '__main__':
    print("🚀 Şikayetvar Scraper API başlatılıyor...")
    print("📍 API: http://localhost:8000")
    print("🔍 Örnek: http://localhost:8000/api/search?q=trendyol")
    print("\n" + "="*50)
    app.run(debug=True, host='0.0.0.0', port=8000)
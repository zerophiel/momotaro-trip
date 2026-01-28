#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script untuk generate laporan penagihan, top spender, top item, dan total omzet dari input-file.txt

PRIVACY NOTICE:
- Script ini memproses data customer termasuk nama dan nomor telepon
- Jangan commit file input-file.txt yang berisi data customer real ke repository
- Gunakan data sample/anonymized untuk testing dan dokumentasi
- Semua contoh di dokumentasi menggunakan data yang di-mask (XXX-XXXX-XXXX)
"""

import re
from collections import defaultdict
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas


def extract_price(text):
    """
    Extract harga dari text item.
    Format: rb (ribu), jt (juta), atau angka dengan titik/koma
    Contoh: "195rb", "1.989.000", "3,4jt" = 3.400.000
    Prioritas: cari yang ada rb/jt dulu, baru format angka panjang
    """
    # Pattern untuk mencari harga dengan prioritas
    # 1. Cari pattern dengan rb/jt (lebih spesifik)
    patterns = [
        (r'(\d+[,\.]?\d*)\s*jt\b', lambda m: float(m.group(1).replace(',', '.')) * 1000000),  # juta
        (r'(\d+[,\.]?\d*)\s*rb\b', lambda m: float(m.group(1).replace(',', '.')) * 1000),  # ribu
    ]
    
    for pattern, converter in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return int(converter(match))
            except:
                continue
    
    # 2. Jika tidak ada rb/jt, cari format angka panjang (minimal 4 digit atau dengan titik)
    long_number_pattern = r'(\d{1,3}(?:\.\d{3})+(?:,\d+)?)'
    match = re.search(long_number_pattern, text)
    if match:
        try:
            num_str = match.group(1).replace('.', '').replace(',', '.')
            return int(float(num_str))
        except:
            pass
    
    return None


def remove_price_from_item_name(text):
    """
    Hapus harga dari nama item.
    Contoh: "Product name isi 40 pcs 439rb" -> "Product name isi 40 pcs"
    """
    # Pattern untuk menghapus harga (sama seperti extract_price tapi untuk removal)
    price_patterns = [
        r'\s*\d+[,\.]?\d*\s*jt\b',  # juta
        r'\s*\d+[,\.]?\d*\s*rb\b',  # ribu
        r'\s*\d{1,3}(?:\.\d{3})+(?:,\d+)?',  # format angka panjang
    ]
    
    result = text
    for pattern in price_patterns:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE).strip()
    
    return result


def remove_notes_from_item_name(text):
    """
    Hapus catatan dalam kurung dari nama item.
    Berdasarkan requirement: "(warna)" di tengah nama item TIDAK dihapus (tetap bagian nama).
    Hanya hapus kurung yang ada di akhir SETELAH harga.
    
    Strategi: Hapus kurung di akhir HANYA jika ada spasi sebelum kurung (menandakan itu catatan terpisah).
    Contoh: "Product name (warna) 109rb" -> setelah hapus harga -> "Product name (warna)"
           Tidak dihapus karena (warna) langsung setelah kata tanpa spasi tambahan (bagian nama).
    
    Contoh: "Product name 125rb (catatan)" -> setelah hapus harga -> "Product name (catatan)"
           Dihapus menjadi "Product name" karena ada spasi sebelum (catatan) di akhir.
    
    Pattern: Hapus kurung di akhir jika ada spasi sebelum kurung (format: "text (notes)")
    """
    # Hapus kurung di akhir jika ada spasi sebelum kurung (menandakan catatan terpisah)
    # Pattern: spasi + kurung di akhir string
    result = re.sub(r'\s+\([^)]*\)\s*$', '', text).strip()
    return result


def extract_quantity_from_customer_name(text):
    """
    Ekstrak quantity dari nama customer jika ada format (+angka) atau (+ angka).
    Contoh: "Customer Name (+10 box)" -> quantity = 10, cleaned_name = "Customer Name"
    Contoh: "Customer Name (+ 11 pack)" -> quantity = 11, cleaned_name = "Customer Name"
    Returns: (quantity, cleaned_name) dimana quantity adalah int atau None jika tidak ditemukan
    """
    # Pattern untuk mencari (+angka) atau (+ angka) dengan berbagai unit (box, pack, butir, dll)
    # Abaikan unit, hanya ambil angka
    quantity_pattern = r'\(\+\s*(\d+)\s*\w*\)'
    match = re.search(quantity_pattern, text, re.IGNORECASE)
    
    if match:
        quantity = int(match.group(1))
        # Hapus pattern dari nama
        cleaned_name = re.sub(quantity_pattern, '', text, flags=re.IGNORECASE).strip()
        return quantity, cleaned_name
    
    return None, text


def extract_notes_from_customer_name(text):
    """
    Ekstrak catatan dalam kurung dari nama customer (untuk ditambahkan ke nama item).
    Hanya ekstrak jika customer sudah checked [x].
    Catatan adalah kurung yang BUKAN quantity format (+angka).
    Contoh: "Customer Name +62 XXX-XXXX-XXXX (catatan tambahan)" -> notes = "(catatan tambahan)", cleaned_name = "Customer Name +62 XXX-XXXX-XXXX"
    Contoh: "Customer Name (+10 box)" -> notes = None (ini quantity, bukan catatan)
    Returns: (notes, cleaned_name) dimana notes adalah string atau None
    """
    # Cari semua kurung dalam text
    # Pattern untuk mencari kurung yang bukan quantity format (+angka)
    notes_pattern = r'\(([^)]+)\)'
    matches = list(re.finditer(notes_pattern, text))
    
    if matches:
        # Cari kurung yang bukan quantity format
        for match in reversed(matches):  # Mulai dari yang paling kanan
            content = match.group(1).strip()
            # Cek apakah ini quantity format (+angka atau + angka)
            if not re.match(r'^\+\s*\d+', content, re.IGNORECASE):
                # Ini adalah catatan, bukan quantity
                notes = f"({content})"
                # Hapus kurung ini dari nama
                before = text[:match.start()].strip()
                after = text[match.end():].strip()
                cleaned_name = f"{before} {after}".strip()
                cleaned_name = re.sub(r'\s+', ' ', cleaned_name).strip()  # Normalize spaces
                return notes, cleaned_name
    
    return None, text


def normalize_unicode(text):
    """
    Normalisasi karakter unicode menjadi karakter standar.
    Menghapus karakter kontrol, non-breaking space, dll.
    """
    if not text:
        return text
    
    # Normalisasi karakter unicode space menjadi spasi biasa
    text = text.replace('\u2009', ' ')  # Thin space
    text = text.replace('\u200A', ' ')  # Hair space
    text = text.replace('\u202F', ' ')  # Narrow no-break space
    text = text.replace('\u00A0', ' ')   # Non-breaking space
    text = text.replace('\u2000', ' ')  # En quad
    text = text.replace('\u2001', ' ')  # Em quad
    text = text.replace('\u2002', ' ')  # En space
    text = text.replace('\u2003', ' ')  # Em space
    text = text.replace('\u2004', ' ')  # Three-per-em space
    text = text.replace('\u2005', ' ')  # Four-per-em space
    text = text.replace('\u2006', ' ')  # Six-per-em space
    text = text.replace('\u2007', ' ')  # Figure space
    text = text.replace('\u2008', ' ')  # Punctuation space
    text = text.replace('\u2009', ' ')  # Thin space
    text = text.replace('\u200A', ' ')  # Hair space
    
    # Hapus zero-width characters
    text = text.replace('\u200B', '')   # Zero-width space
    text = text.replace('\u200C', '')   # Zero-width non-joiner
    text = text.replace('\u200D', '')   # Zero-width joiner
    text = text.replace('\uFEFF', '')   # Zero-width no-break space
    text = text.replace('\u202A', '')   # Left-to-right embedding
    text = text.replace('\u202B', '')   # Right-to-left embedding
    text = text.replace('\u202C', '')   # Pop directional formatting
    text = text.replace('\u202D', '')   # Left-to-right override
    text = text.replace('\u202E', '')   # Right-to-left override
    text = text.replace('\u2066', '')   # Left-to-right isolate
    text = text.replace('\u2067', '')   # Right-to-left isolate
    text = text.replace('\u2068', '')   # First strong isolate
    text = text.replace('\u2069', '')   # Pop directional isolate
    text = text.replace('\u200E', '')   # Left-to-right mark
    text = text.replace('\u200F', '')   # Right-to-left mark
    text = text.replace('\u2028', ' ')  # Line separator -> space
    text = text.replace('\u2029', ' ')  # Paragraph separator -> space
    
    # Normalisasi dash/hyphen unicode menjadi dash biasa
    text = text.replace('\u2011', '-')  # Non-breaking hyphen
    text = text.replace('\u2012', '-')  # Figure dash
    text = text.replace('\u2013', '-')  # En dash
    text = text.replace('\u2014', '-')  # Em dash
    text = text.replace('\u2015', '-')  # Horizontal bar
    text = text.replace('\u2212', '-')  # Minus sign
    text = text.replace('\uFE63', '-')  # Small hyphen-minus
    text = text.replace('\uFF0D', '-')  # Fullwidth hyphen-minus
    text = text.replace('\u00AD', '-')  # Soft hyphen
    text = text.replace('\u2010', '-')  # Hyphen
    
    return text


def normalize_phone(phone):
    """Normalize nomor telepon untuk perbandingan"""
    if not phone:
        return None
    # Hapus semua karakter non-digit kecuali +
    phone_clean = re.sub(r'[^\d+]', '', phone)
    # Normalize format: +62 atau 0 di awal menjadi format standar
    if phone_clean.startswith('+62'):
        phone_clean = phone_clean.replace('+62', '0')
    elif phone_clean.startswith('62'):
        phone_clean = '0' + phone_clean[2:]
    # Pastikan dimulai dengan 0
    if not phone_clean.startswith('0'):
        phone_clean = '0' + phone_clean
    return phone_clean


def normalize_customer_name(name):
    """Normalize nama customer (case-insensitive)"""
    if not name:
        return ""
    return name.strip().lower()


def get_customer_key(name, phone):
    """
    Generate key untuk customer berdasarkan nama dan no telp.
    Jika ada no telp, gunakan no telp sebagai key utama.
    Jika tidak ada no telp, gunakan nama (case-insensitive).
    """
    normalized_phone = normalize_phone(phone)
    normalized_name = normalize_customer_name(name)
    
    if normalized_phone:
        return f"{normalized_phone}_{normalized_name}"
    else:
        return f"NO_PHONE_{normalized_name}"


def parse_input_file(filename):
    """
    Parse input file dan return data struktur:
    {
        'items': [
            {
                'name': 'Item name',
                'price': 125000,
                'customers': [
                    {'name': 'Customer', 'phone': '+62...', 'checked': True/False}
                ]
            }
        ],
        'customers': {
            'customer_key': {'name': 'Customer', 'phone': '+62...'}
        }
    }
    """
    items = []
    customers = {}
    current_item = None
    skip_section = False
    
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Normalisasi unicode di awal (sebelum semua proses)
            line = normalize_unicode(line)
            
            # Check jika masuk section "Product REQUEST cek harga"
            if "Product REQUEST cek harga" in line:
                skip_section = True
                continue
            
            # Skip semua item di section tersebut
            if skip_section:
                continue
            
            # Check jika ini item baru (ada harga di line)
            price = extract_price(line)
            if price is not None:
                # Simpan item sebelumnya jika ada
                if current_item:
                    items.append(current_item)
                
                # Extract nama item tanpa harga
                item_name = remove_price_from_item_name(line)
                # Hapus catatan dalam kurung yang ada setelah harga atau di akhir
                item_name = remove_notes_from_item_name(item_name)
                
                # Buat item baru
                current_item = {
                    'name': item_name,
                    'price': price,
                    'customers': []
                }
            else:
                # Ini adalah customer line
                if current_item is None:
                    continue
                
                # Parse customer line
                # Format: "- [x] Customer Name +62..." atau "1. Customer Name +62..."
                checked = False
                customer_text = line
                
                # Check untuk checkbox [x]
                if '- [x]' in line:
                    checked = True
                    customer_text = line.replace('- [x]', '').strip()
                elif '- [ ]' in line or '- []' in line:
                    checked = False
                    customer_text = line.replace('- [ ]', '').replace('- []', '').strip()
                elif re.match(r'^\d+\.', line):
                    # Format "1. Customer Name"
                    checked = False
                    customer_text = re.sub(r'^\d+\.\s*', '', line).strip()
                elif line.startswith('- '):
                    # Format "- Customer Name" (tanpa checkbox)
                    checked = False
                    customer_text = line.replace('- ', '').strip()
                
                # Normalisasi unicode sudah dilakukan di awal, tapi pastikan lagi
                customer_text = normalize_unicode(customer_text)
                
                # Ekstrak quantity terlebih dahulu (sebelum menghapus kurung lainnya)
                quantity, customer_text_temp = extract_quantity_from_customer_name(customer_text)
                if quantity is None:
                    quantity = 1  # Default quantity = 1
                else:
                    customer_text = customer_text_temp
                
                # Ekstrak notes (catatan dalam kurung) untuk ditambahkan ke nama item
                # Hanya jika customer checked [x]
                # Notes harus diekstrak SETELAH quantity (karena quantity format juga pakai kurung)
                notes = None
                if checked:
                    notes, customer_text = extract_notes_from_customer_name(customer_text)
                
                # Hapus kata "ok" di akhir (case-insensitive) dan teks dalam kurung yang mungkin ada
                # Urutan penting: 
                # 1. Hapus "ok" yang ada sebelum kurung
                # 2. Hapus kurung beserta "ok" yang mungkin ada setelahnya (dengan atau tanpa spasi)
                # 3. Hapus "ok" di akhir jika masih ada
                customer_text = re.sub(r'\s+ok\s*\(', ' (', customer_text, flags=re.IGNORECASE).strip()  # Hapus "ok" sebelum kurung
                customer_text = re.sub(r'\s*\([^)]*\)\s*ok\s*$', '', customer_text, flags=re.IGNORECASE).strip()  # Hapus kurung dan "ok" setelahnya (dengan spasi)
                customer_text = re.sub(r'\s*\([^)]*\)ok\s*$', '', customer_text, flags=re.IGNORECASE).strip()  # Hapus kurung dan "ok" setelahnya (tanpa spasi)
                # Hapus kurung yang tersisa (jika masih ada setelah ekstraksi notes dan quantity)
                customer_text = re.sub(r'\s*\([^)]*\)\s*$', '', customer_text).strip()  # Hapus teks dalam kurung di akhir (jika masih ada)
                customer_text = re.sub(r'\s+ok\s*$', '', customer_text, flags=re.IGNORECASE).strip()  # Hapus "ok" di akhir
                # Normalisasi spasi ganda menjadi spasi tunggal
                customer_text = re.sub(r'\s+', ' ', customer_text).strip()
                
                # Extract nama dan nomor telepon
                # Strategi: cari semua kemungkinan nomor telepon, ambil yang paling kanan (terakhir)
                # Pattern harus lebih fleksibel untuk menangkap berbagai format
                phone_patterns = [
                    r'(\+62\s+\d{3}-\d{4}-\d{4})',  # +62 XXX-XXXX-XXXX format (3-4-4)
                    r'(\+62\s+\d{3}-\d{4}-\d{3})',  # +62 XXX-XXXX-XXX format (3-4-3)
                    r'(\+62\s+\d{3}-\d{3}-\d{3})',  # +62 XXX-XXX-XXX format (3-3-3)
                    r'(\+62\s+\d{2}-\d{4}-\d{4})',  # +62 81-1234-5678 format (2-4-4)
                    r'(\+62\s+\d{3}\s+\d{4}\s+\d{4})',  # +62 XXX XXXX XXXX format dengan spasi (3-4-4)
                    r'(\+62\s+\d{2}\s+\d{4}\s+\d{4})',  # +62 81 1234 5678 format dengan spasi (2-4-4)
                    r'(\+62\s+\d{2,3}[-.\s]\d{3,4}[-.\s]\d{3,4}[-.\s]\d{3,4})',  # +62 dengan separator
                    r'(\+62\s*\d{2,3}[-.\s]?\d{3,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4})',  # +62 format umum
                    r'(0\d{2,3}[-.\s]?\d{3,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4})',  # 08 format dengan separator
                    r'(0\d{10,12})(?=\s|$)',  # 08XXXXXXXXXX format tanpa separator
                ]
                
                phone_match = None
                all_matches = []
                
                # Kumpulkan semua match dari semua pattern
                for pattern in phone_patterns:
                    matches = list(re.finditer(pattern, customer_text))
                    all_matches.extend(matches)
                
                if all_matches:
                    # Ambil yang paling kanan (terakhir) - ini biasanya nomor telepon yang benar
                    phone_match = max(all_matches, key=lambda m: m.end())
                
                if phone_match:
                    phone = phone_match.group(1).strip()
                    name = customer_text[:phone_match.start()].strip()
                    
                    # Normalisasi nomor telepon: jika dimulai dengan 0, ubah menjadi +62
                    # Contoh: "08XXXXXXXXXX" -> "+62 XXX-XXXX-XXX"
                    if phone.startswith('0'):
                        # Hapus semua non-digit untuk mendapatkan hanya angka
                        digits = re.sub(r'[^\d]', '', phone)
                        if len(digits) >= 10 and digits.startswith('0'):
                            # Hapus 0 di awal
                            digits = digits[1:]
                            # Format menjadi +62 dengan dash
                            if len(digits) == 10:
                                # Format: XXXXXXXXXX -> +62 XXX-XXXX-XXX
                                phone = f"+62 {digits[0:3]}-{digits[3:7]}-{digits[7:]}"
                            elif len(digits) == 11:
                                # Format: XXXXXXXXXXX -> +62 XXX-XXXX-XXXX
                                phone = f"+62 {digits[0:3]}-{digits[3:7]}-{digits[7:]}"
                            elif len(digits) == 9:
                                # Format: XXXXXXXXX -> +62 XXX-XXXX-XX
                                phone = f"+62 {digits[0:3]}-{digits[3:7]}-{digits[7:]}"
                else:
                    phone = None
                    name = customer_text.strip()
                
                # Hanya tambahkan jika checked (ada [x])
                if checked:
                    customer_key = get_customer_key(name, phone)
                    
                    # Simpan customer info
                    if customer_key not in customers:
                        customers[customer_key] = {
                            'name': name,
                            'phone': phone
                        }
                    
                    # Tambahkan ke item dengan quantity dan notes
                    current_item['customers'].append({
                        'name': name,
                        'phone': phone,
                        'checked': checked,
                        'quantity': quantity,
                        'notes': notes  # Catatan untuk ditambahkan ke nama item di laporan
                    })
        
        # Tambahkan item terakhir
        if current_item:
            items.append(current_item)
    
    return items, customers


def format_currency(amount):
    """Format angka menjadi format Rupiah: Rp. 125.000,-"""
    formatted = f"{amount:,.0f}".replace(',', '.')
    return f"Rp. {formatted},-"


def generate_billing_report(items, customers, filename):
    """Generate PDF laporan penagihan per customer"""
    doc = SimpleDocTemplate(filename, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    customer_header_style = ParagraphStyle(
        'CustomerHeader',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=10,
        spaceBefore=20
    )
    
    # Title
    story.append(Paragraph("Laporan Penagihan", title_style))
    story.append(Spacer(1, 0.5*cm))
    
    # Group items by customer dengan quantity dan notes
    customer_purchases = defaultdict(list)
    
    for item in items:
        for customer_entry in item['customers']:
            if customer_entry['checked']:
                customer_key = get_customer_key(
                    customer_entry['name'],
                    customer_entry['phone']
                )
                # Gunakan quantity dari customer_entry (default 1 jika tidak ada)
                quantity = customer_entry.get('quantity', 1)
                # Tambahkan notes ke nama item jika ada
                item_name = item['name']
                notes = customer_entry.get('notes')
                if notes:
                    item_name = f"{item['name']} {notes}"
                
                customer_purchases[customer_key].append({
                    'item_name': item_name,
                    'price': item['price'],
                    'quantity': quantity
                })
    
    # Count quantities per customer per item (dengan notes)
    customer_items = defaultdict(lambda: defaultdict(int))
    for customer_key, purchases in customer_purchases.items():
        for purchase in purchases:
            # Key adalah item_name dengan notes (jika ada)
            customer_items[customer_key][purchase['item_name']] += purchase['quantity']
    
    # Sort customers alphabetically by name
    sorted_customers = sorted(
        customers.items(),
        key=lambda x: x[1]['name'].lower()
    )
    
    # Generate table for each customer
    for customer_key, customer_info in sorted_customers:
        if customer_key not in customer_items:
            continue
        
        # Customer header
        customer_name = customer_info['name']
        customer_phone = customer_info['phone'] or "Tidak ada nomor telepon"
        
        header_text = f"<b>{customer_name}</b><br/>{customer_phone}"
        story.append(Paragraph(header_text, customer_header_style))
        story.append(Spacer(1, 0.3*cm))
        
        # Table data
        table_data = [['No', 'Nama Item', 'Jumlah', 'Harga Satuan', 'Subtotal']]
        
        item_list = customer_items[customer_key]
        total = 0
        row_num = 1
        
        for item_name_with_notes, quantity in sorted(item_list.items()):
            # Extract item name tanpa notes untuk mencari harga
            # Notes format: "Item Name (notes)" atau "Item Name"
            item_name = item_name_with_notes
            # Hapus notes jika ada (format: "Item Name (notes)")
            notes_match = re.search(r'^(.+?)\s*\([^)]+\)$', item_name_with_notes)
            if notes_match:
                item_name = notes_match.group(1).strip()
            
            # Find price for this item
            item_price = None
            for item in items:
                if item['name'] == item_name:
                    item_price = item['price']
                    break
            
            if item_price is None:
                continue
            
            subtotal = item_price * quantity
            total += subtotal
            
            table_data.append([
                str(row_num),
                item_name_with_notes,  # Gunakan nama dengan notes untuk display
                str(quantity),
                format_currency(item_price),
                format_currency(subtotal)
            ])
            row_num += 1
        
        # Add grand total row - gunakan Paragraph untuk bold text (Table tidak support HTML)
        grand_total_style = ParagraphStyle(
            'GrandTotal',
            parent=styles['Normal'],
            fontSize=11,
            fontName='Helvetica-Bold',
            alignment=TA_LEFT
        )
        grand_total_currency_style = ParagraphStyle(
            'GrandTotalCurrency',
            parent=styles['Normal'],
            fontSize=11,
            fontName='Helvetica-Bold',
            alignment=TA_RIGHT
        )
        
        table_data.append([
            '',
            Paragraph('GRAND TOTAL', grand_total_style),
            '',
            '',
            Paragraph(format_currency(total), grand_total_currency_style)
        ])
        
        # Create table
        table = Table(table_data, colWidths=[1*cm, 8*cm, 2*cm, 3*cm, 3*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 11),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ecf0f1')),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 1*cm))
    
    # Add page numbers
    def add_page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        page_num = canvas.getPageNumber()
        text = f"Halaman {page_num}"
        canvas.drawRightString(A4[0] - 2*cm, 2*cm, text)
        canvas.restoreState()
    
    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    print(f"[OK] Laporan penagihan berhasil dibuat: {filename}")


def generate_top_spender_report(items, customers, filename):
    """Generate PDF laporan top 5 spender"""
    doc = SimpleDocTemplate(filename, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    # Title
    story.append(Paragraph("Laporan Top 5 Spender", title_style))
    story.append(Spacer(1, 0.5*cm))
    
    # Calculate total spending per customer (dengan menghitung quantity)
    customer_totals = defaultdict(int)
    customer_item_counts = defaultdict(lambda: defaultdict(int))
    
    # Count quantities per customer per item (gunakan quantity dari customer_entry)
    for item in items:
        for customer_entry in item['customers']:
            if customer_entry['checked']:
                customer_key = get_customer_key(
                    customer_entry['name'],
                    customer_entry['phone']
                )
                quantity = customer_entry.get('quantity', 1)
                customer_item_counts[customer_key][item['name']] += quantity
    
    # Calculate totals
    for customer_key, item_counts in customer_item_counts.items():
        for item in items:
            if item['name'] in item_counts:
                customer_totals[customer_key] += item['price'] * item_counts[item['name']]
    
    # Get top 5
    top_spenders = sorted(
        customer_totals.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    # Table data
    table_data = [['No', 'Nama Customer', 'Nomor Telepon', 'Total Pembelian']]
    
    for idx, (customer_key, total) in enumerate(top_spenders, 1):
        customer_info = customers.get(customer_key, {})
        name = customer_info.get('name', 'Unknown')
        phone = customer_info.get('phone', 'Tidak ada nomor telepon')
        
        table_data.append([
            str(idx),
            name,
            phone,
            format_currency(total)
        ])
    
    # Create table
    table = Table(table_data, colWidths=[1.5*cm, 6*cm, 5*cm, 4*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
    ]))
    
    story.append(table)
    doc.build(story)
    print(f"[OK] Laporan top spender berhasil dibuat: {filename}")


def generate_top_item_report(items, customers, filename):
    """Generate PDF laporan top 5 item"""
    doc = SimpleDocTemplate(filename, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    # Title
    story.append(Paragraph("Laporan Top 5 Item", title_style))
    story.append(Spacer(1, 0.5*cm))
    
    # Calculate total quantity per item (gunakan quantity dari customer_entry)
    item_totals = defaultdict(int)
    
    for item in items:
        for customer_entry in item['customers']:
            if customer_entry['checked']:
                quantity = customer_entry.get('quantity', 1)
                item_totals[item['name']] += quantity
    
    # Get top 5
    top_items = sorted(
        item_totals.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    # Table data
    table_data = [['No', 'Nama Item', 'Jumlah Terjual']]
    
    for idx, (item_name, quantity) in enumerate(top_items, 1):
        table_data.append([
            str(idx),
            item_name,
            str(quantity)
        ])
    
    # Create table
    table = Table(table_data, colWidths=[1.5*cm, 12*cm, 4*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
    ]))
    
    story.append(table)
    doc.build(story)
    print(f"[OK] Laporan top item berhasil dibuat: {filename}")


def generate_total_omzet_report(items, customers, filename):
    """Generate PDF laporan total omzet"""
    doc = SimpleDocTemplate(filename, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    # Title
    story.append(Paragraph("Laporan Total Omzet", title_style))
    story.append(Spacer(1, 0.5*cm))
    
    # Calculate total revenue per item and overall totals
    item_revenue = defaultdict(int)
    item_quantity = defaultdict(int)
    total_omzet = 0
    total_quantity = 0
    total_items_sold = 0
    
    for item in items:
        item_name = item['name']
        item_price = item['price']
        quantity = 0
        
        for customer_entry in item['customers']:
            if customer_entry['checked']:
                qty = customer_entry.get('quantity', 1)
                quantity += qty
                item_revenue[item_name] += item_price * qty
                total_omzet += item_price * qty
                total_quantity += qty
        
        if quantity > 0:
            item_quantity[item_name] = quantity
            total_items_sold += 1
    
    # Summary section
    summary_style = ParagraphStyle(
        'Summary',
        parent=styles['Normal'],
        fontSize=12,
        fontName='Helvetica-Bold',
        spaceAfter=20
    )
    
    story.append(Paragraph("Ringkasan", summary_style))
    story.append(Spacer(1, 0.2*cm))
    
    # Summary table
    summary_data = [
        ['Total Omzet', format_currency(total_omzet)],
        ['Total Item Terjual', f"{total_items_sold} item"],
        ['Total Quantity', f"{total_quantity} unit"],
        ['Total Customer', f"{len(customers)} customer"]
    ]
    
    summary_table = Table(summary_data, colWidths=[8*cm, 8*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ecf0f1')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 0.5*cm))
    
    # Detail per item section
    detail_title_style = ParagraphStyle(
        'DetailTitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=10,
        spaceBefore=20
    )
    
    story.append(Paragraph("Detail Omzet per Item", detail_title_style))
    story.append(Spacer(1, 0.3*cm))
    
    # Sort items by revenue (descending)
    sorted_items = sorted(
        item_revenue.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    # Table data
    table_data = [['No', 'Nama Item', 'Quantity', 'Harga Satuan', 'Total Revenue']]
    
    for idx, (item_name, revenue) in enumerate(sorted_items, 1):
        quantity = item_quantity[item_name]
        # Find unit price
        unit_price = None
        for item in items:
            if item['name'] == item_name:
                unit_price = item['price']
                break
        
        if unit_price is None:
            continue
        
        table_data.append([
            str(idx),
            item_name,
            str(quantity),
            format_currency(unit_price),
            format_currency(revenue)
        ])
    
    # Add grand total row
    grand_total_style = ParagraphStyle(
        'GrandTotal',
        parent=styles['Normal'],
        fontSize=11,
        fontName='Helvetica-Bold',
        alignment=TA_LEFT
    )
    grand_total_currency_style = ParagraphStyle(
        'GrandTotalCurrency',
        parent=styles['Normal'],
        fontSize=11,
        fontName='Helvetica-Bold',
        alignment=TA_RIGHT
    )
    
    table_data.append([
        '',
        Paragraph('TOTAL OMZET', grand_total_style),
        str(total_quantity),
        '',
        Paragraph(format_currency(total_omzet), grand_total_currency_style)
    ])
    
    # Create table
    table = Table(table_data, colWidths=[1.5*cm, 7*cm, 2.5*cm, 3*cm, 3*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (2, 0), (4, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -2), 10),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 11),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ecf0f1')),
    ]))
    
    story.append(table)
    doc.build(story)
    print(f"[OK] Laporan total omzet berhasil dibuat: {filename}")


def main():
    input_file = 'input-file.txt'
    
    print("Memulai proses parsing file...")
    items, customers = parse_input_file(input_file)
    
    print(f"[OK] Ditemukan {len(items)} item")
    print(f"[OK] Ditemukan {len(customers)} customer")
    
    print("\nMembuat laporan PDF...")
    generate_billing_report(items, customers, 'laporan_penagihan.pdf')
    generate_top_spender_report(items, customers, 'laporan_top_spender.pdf')
    generate_top_item_report(items, customers, 'laporan_top_item.pdf')
    generate_total_omzet_report(items, customers, 'laporan_total_omzet.pdf')
    
    print("\n[OK] Semua laporan berhasil dibuat!")


if __name__ == '__main__':
    main()

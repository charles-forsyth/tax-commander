import os
import qrcode
import urllib.parse
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class TaxBiller:
    def __init__(self, output_dir="tax_bills", org_config=None):
        self.output_dir = output_dir
        self.org_config = org_config or {}
        
        os.makedirs(self.output_dir, exist_ok=True)
        self.styles = getSampleStyleSheet()
        self.styles.add(ParagraphStyle(name='BodyTextBold', parent=self.styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=12))
        self.styles.add(ParagraphStyle(name='Address', parent=self.styles['Normal'], fontSize=11, leading=14))
        self.styles.add(ParagraphStyle(name='HeaderTitle', parent=self.styles['h1'], fontName='Helvetica-Bold', fontSize=18, leading=22, alignment=1)) # Increased font size
        self.styles.add(ParagraphStyle(name='HeaderSub', parent=self.styles['Normal'], fontSize=12, leading=14, alignment=1))
        self.styles.add(ParagraphStyle(name='SmallText', parent=self.styles['Normal'], fontSize=9, leading=11))
        self.styles.add(ParagraphStyle(name='SmallBold', parent=self.styles['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=11))

    def generate_bill(self, parcel_data, bill_type="Township_County", output_dir=None, date_suffix=None):
        """
        Generates a PDF tax bill for a single parcel using a balanced, professional layout (no logo).
        """
        parcel_id = parcel_data['parcel_id']
        target_dir = output_dir if output_dir else self.output_dir
        
        # Extract Config
        org = self.org_config.get('organization', self.org_config)
        contact = self.org_config.get('contact', {})
        
        collector_name = org.get('collector_name', 'Tax Collector Name')
        collector_title = org.get('collector_title', 'Tax Collector')
        address = org.get('mailing_address', '123 Main St')
        city_zip = org.get('city_state_zip', 'City, State Zip')
        township_name = org.get('township_name', 'MUNICIPALITY NAME')
        
        # Filename
        suffix = f"_{date_suffix}" if date_suffix else ""
        filename = f"{bill_type}_{parcel_id}_Bill{suffix}.pdf"
        output_filename = os.path.join(target_dir, filename)
        
        # Standard Letter Margins (0.75 inch) for professional look
        doc = SimpleDocTemplate(output_filename, pagesize=letter, 
                                topMargin=0.75*inch, bottomMargin=0.5*inch, 
                                leftMargin=0.75*inch, rightMargin=0.75*inch) # Increased top margin
        story = []

        # --- 1. Header Section (Text Only) ---
        story.append(Paragraph(f"{township_name} TAX NOTICE", self.styles['HeaderTitle']))
        story.append(Paragraph(f"{bill_type.replace('_', ' ').upper()}", self.styles['HeaderSub']))
        story.append(Spacer(1, 0.4 * inch)) # Generous spacing after header

        # --- 2. Address Block ---
        story.append(Paragraph(parcel_data['owner_name'], self.styles['Address']))
        story.append(Paragraph(parcel_data['mailing_address'], self.styles['Address']))
        
        # Spacer to push the main table down a bit
        story.append(Spacer(1, 0.4 * inch))

        # --- 3. Main Data Grid ---
        
        # Left Column: Property & Financials
        left_col = []
        left_col.append(Paragraph(f"<b>PROPERTY DETAILS</b>", self.styles['BodyTextBold']))
        left_col.append(Spacer(1, 0.05*inch))
        left_col.append(Paragraph(f"Parcel ID: {parcel_id}", self.styles['Normal']))
        left_col.append(Paragraph(f"Bill #: {parcel_data['bill_number']}", self.styles['Normal']))
        left_col.append(Paragraph(f"Assessed Value: ${parcel_data['assessment_value']:.2f}", self.styles['Normal']))
        left_col.append(Paragraph(f"Location: {parcel_data['property_address']}", self.styles['Normal']))
        left_col.append(Spacer(1, 0.2 * inch))
        
        left_col.append(Paragraph(f"<b>PAYMENT SCHEDULE</b>", self.styles['BodyTextBold']))
        left_col.append(Spacer(1, 0.05*inch))
        
        issue_date = datetime.strptime(parcel_data['bill_issue_date'], '%Y-%m-%d')
        disc_end = (issue_date + relativedelta(months=2) - timedelta(days=1)).strftime('%b %d')
        face_end = (issue_date + relativedelta(months=2)).strftime('%b %d')
        penalty_start = (issue_date + relativedelta(months=4)).strftime('%b %d')

        # Styled boxes for amounts
        left_col.append(Paragraph(f"<b>• Discount: ${parcel_data['discount_amount']:.2f}</b> (by {disc_end})", self.styles['Normal']))
        left_col.append(Paragraph(f"<b>• Face:     ${parcel_data['face_tax_amount']:.2f}</b> (by {face_end})", self.styles['Normal']))
        left_col.append(Paragraph(f"<b>• Penalty:  ${parcel_data['penalty_amount']:.2f}</b> (on/after {penalty_start})", self.styles['Normal']))

        # Right Column: Instructions & Contact
        right_col = []
        right_col.append(Paragraph("<b>HOW TO PAY</b>", self.styles['BodyTextBold']))
        right_col.append(Spacer(1, 0.05*inch))
        right_col.append(Paragraph(f"<b>Payable to:</b> {township_name} {collector_title}", self.styles['Normal']))
        right_col.append(Paragraph(f"<b>Mail to:</b><br/>{collector_name}<br/>{address}<br/>{city_zip}", self.styles['Normal']))
        
        drop_msg = contact.get('drop_box_message')
        if drop_msg:
            right_col.append(Spacer(1, 0.1 * inch))
            right_col.append(Paragraph(f"<b>{drop_msg}</b>", self.styles['BodyTextBold']))
        
        # QR Code Logic
        qr_conf = contact.get('qr_code', {})
        qr_file_path = None
        if qr_conf.get('enabled', False):
            email = contact.get('email', '')
            if email:
                # 1. Prepare Content
                subject = qr_conf.get('subject_template', 'Tax Inquiry - {parcel_id}').format(parcel_id=parcel_id)
                body_tpl = qr_conf.get('body_template', 'Hello {collector_name},')
                body = body_tpl.format(
                    parcel_id=parcel_id,
                    collector_name=collector_name,
                    owner_name=parcel_data['owner_name']
                )

                # 2. URL Encode (Critical for special chars and newlines in mailto)
                subject_enc = urllib.parse.quote(subject)
                body_enc = urllib.parse.quote(body)
                
                # 3. Build Link
                mailto_link = f"mailto:{email}?subject={subject_enc}&body={body_enc}"
                
                # 4. Generate Image
                qr = qrcode.QRCode(box_size=3, border=1) # Smaller box size for cleaner look
                qr.add_data(mailto_link)
                qr.make(fit=True)
                img = qr.make_image(fill='black', back_color='white')
                qr_file_path = f"temp_qr_{parcel_id}.png"
                img.save(qr_file_path)
                
                right_col.append(Spacer(1, 0.2 * inch))
                right_col.append(Paragraph("<b>Have a Question? Scan to Email:</b>", self.styles['SmallText']))
                right_col.append(Image(qr_file_path, width=1.0*inch, height=1.0*inch))

        # Grid Table Setup
        table_data = [[left_col, right_col]]
        table = Table(table_data, colWidths=[3.5*inch, 3.5*inch])
        table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(table)
        
        # Spacer to push down
        story.append(Spacer(1, 0.5 * inch))

        # --- 4. Community/FAQ Section ---
        story.append(Paragraph("<b>IMPORTANT INFORMATION</b>", self.styles['SmallBold']))
        faq_text = "<b>Partial Payments:</b> Only allowed via official Installment Plan (1st payment due by Face deadline).&nbsp;&nbsp;<b>Missed Deadline:</b> Postmark date determines payment period."
        story.append(Paragraph(faq_text, self.styles['SmallText']))
        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph(f"<i>Thank you for supporting {township_name}.</i>", self.styles['SmallText']))

        # --- SPRING SPACER to Push Stub to Bottom ---
        story.append(Spacer(1, 1.5 * inch))

        # --- 5. Remittance Stub ---
        story.append(Paragraph("- " * 75, self.styles['SmallText'])) # Dashed line
        story.append(Paragraph("<i>Please detach and return this portion with your payment.</i>", self.styles['SmallText']))
        story.append(Spacer(1, 0.2 * inch))

        # Stub Table
        stub_left = [
            Paragraph(f"<b>REMITTANCE STUB</b>", self.styles['BodyTextBold']),
            Paragraph(f"<b>{township_name.upper()} TAX</b>", self.styles['Normal']),
            Paragraph(f"{parcel_data['owner_name']}", self.styles['Normal']),
            Paragraph(f"Parcel: {parcel_id}", self.styles['Normal']),
            Paragraph(f"Bill #: {parcel_data['bill_number']}", self.styles['Normal']),
        ]
        
        stub_right = [
            Paragraph("<b>Payment Amount Enclosed:</b>", self.styles['BodyTextBold']),
            Paragraph(f"Check One:", self.styles['SmallText']),
            Paragraph(f"[ ] Discount: ${parcel_data['discount_amount']:.2f}", self.styles['Normal']),
            Paragraph(f"[ ] Face:     ${parcel_data['face_tax_amount']:.2f}", self.styles['Normal']),
            Paragraph(f"[ ] Penalty:  ${parcel_data['penalty_amount']:.2f}", self.styles['Normal']),
        ]
        
        if parcel_data['is_installment_plan']:
             inst_amt = round(parcel_data['face_tax_amount'] / 3, 2)
             stub_right.append(Paragraph(f"[ ] Installment: ${inst_amt:.2f}", self.styles['Normal']))

        stub_right.append(Spacer(1, 0.1 * inch))
        stub_right.append(Paragraph("<b>$_______________________</b>", self.styles['HeaderSub']))

        stub_table = Table([[stub_left, stub_right]], colWidths=[4.0*inch, 3.0*inch])
        stub_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (1,0), (1,0), 'LEFT'), # Align check boxes
        ]))
        story.append(stub_table)

        try:
            doc.build(story)
            print(f"Generated bill for {parcel_id} at {output_filename}")
        except Exception as e:
            print(f"Error generating bill for {parcel_id}: {e}")
        finally:
            # Cleanup QR temp file
            if qr_file_path and os.path.exists(qr_file_path):
                os.remove(qr_file_path)

    def generate_all_bills(self, db_manager, bill_type="Township_County"):
        """
        Generates bills for all parcels in the database.
        Creates a timestamped subfolder: tax_bills/YYYY-MM_BillType/
        """
        db_manager.connect()
        query = "SELECT * FROM tax_duplicate"
        parcels = db_manager.conn.execute(query).fetchall()
        db_manager.disconnect()

        if not parcels:
            print("No parcels found in the database to generate bills.")
            return

        # Create Date-Stamped Batch Folder
        date_str = datetime.now().strftime("%Y-%m")
        batch_folder_name = f"{date_str}_{bill_type}"
        batch_dir = os.path.join(self.output_dir, batch_folder_name)
        os.makedirs(batch_dir, exist_ok=True)

        print(f"Generating {bill_type.replace('_', ' ')} tax bills in {batch_dir}...")
        
        for parcel in parcels:
            self.generate_bill(parcel, bill_type, output_dir=batch_dir, date_suffix=date_str)
            
        print(f"All {bill_type.replace('_', ' ')} bills generated in {batch_dir}/")

    def reprint_bill(self, db_manager, parcel_id, bill_type="Township_County"):
        """
        Regenerates a single bill for a specific parcel.
        """
        db_manager.connect()
        query = "SELECT * FROM tax_duplicate WHERE parcel_id = ?"
        parcel = db_manager.conn.execute(query, (parcel_id,)).fetchone()
        db_manager.disconnect()

        if not parcel:
            print(f"Error: Parcel ID {parcel_id} not found.")
            return

        reprint_dir = os.path.join(self.output_dir, "reprints")
        os.makedirs(reprint_dir, exist_ok=True)
        
        print(f"Reprinting {bill_type} bill for {parcel_id}...")
        
        self.generate_bill(parcel, bill_type, output_dir=reprint_dir, date_suffix="REPRINT")
        print(f"Bill reprinted to {reprint_dir}/")

# For local testing
if __name__ == "__main__":
    from db_manager import DBManager
    # Ensure dummy data and DB are set up for testing biller.py directly
    # In a real scenario, you'd run `tax_commander.py init-db` and `import-duplicate` first
    db_manager = DBManager()
    biller = TaxBiller()
    biller.generate_all_bills(db_manager, "Township_County")
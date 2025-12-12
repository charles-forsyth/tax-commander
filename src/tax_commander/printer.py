import os
import subprocess
import csv
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

class PrintManager:
    def __init__(self, config=None):
        self.config = config or {}

    def list_printers(self):
        """Lists available CUPS printers."""
        try:
            result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
            print("\n🖨️  Available Printers:")
            for line in result.stdout.split('\n'):
                if "printer" in line:
                    parts = line.split()
                    if len(parts) > 1:
                        print(f"   - {parts[1]}")
            print("\n(Use one of these names for the --printer argument)")
        except FileNotFoundError:
            print("Error: 'lpstat' command not found. Is CUPS installed?")

    def print_file(self, file_path, printer_name=None):
        """Sends a specific file to the printer via CUPS."""
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return False

        cmd = ['lp']
        if printer_name:
            cmd.extend(['-d', printer_name])
        cmd.append(file_path)

        try:
            subprocess.run(cmd, check=True)
            print(f"✅ Sent to printer: {os.path.basename(file_path)}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Print failed for {file_path}: {e}")
            return False

    def batch_print_folder(self, folder_path, printer_name=None):
        """Prints all PDF files in a folder."""
        if not os.path.exists(folder_path):
            print(f"Error: Folder not found: {folder_path}")
            return

        files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
        if not files:
            print("No PDF files found in this folder.")
            return

        print(f"🖨️  Batch printing {len(files)} files from {folder_path}...")
        
        # Sort files to ensure order (usually by Parcel ID if named correctly)
        files.sort()

        for f in files:
            full_path = os.path.join(folder_path, f)
            self.print_file(full_path, printer_name)

class LabelGenerator:
    def __init__(self):
        # Avery 5160 Specifications
        self.pagesize = letter
        self.labels_across = 3
        self.labels_down = 10
        self.label_width = 2.625 * inch
        self.label_height = 1.0 * inch
        self.left_margin = 0.1875 * inch
        self.top_margin_offset = 0.5 * inch # Distance from top edge to first label
        self.col_gutter = 0.125 * inch
        self.row_gutter = 0.0 * inch

    def generate_pdf(self, csv_path, output_filename="Labels_Printable.pdf"):
        """Generates a printable PDF from the mailing labels CSV."""
        if not os.path.exists(csv_path):
            print(f"Error: CSV file not found at {csv_path}")
            return None

        c = canvas.Canvas(output_filename, pagesize=self.pagesize)
        width, height = self.pagesize
        
        # Read CSV
        data = []
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)

        print(f"Generating label sheet for {len(data)} addresses...")

        col = 0
        row = 0
        
        # Iterate through data
        for item in data:
            # Calculate coordinates
            # X: Left Margin + (Col Index * (Label Width + Gutter))
            x = self.left_margin + (col * (self.label_width + self.col_gutter))
            
            # Y: Page Height - Top Margin - ((Row Index + 1) * Label Height)
            # Note: PDF coordinates start from bottom-left.
            y = height - self.top_margin_offset - (row * self.label_height) - (0.8 * inch) 
            # 0.8 inch adjustment to get inside the label from its top edge

            # Draw Text
            text_object = c.beginText(x + 0.1 * inch, y + 0.6 * inch) # Padding inside label
            text_object.setFont("Helvetica", 10)
            
            name = item.get('Name', 'Resident')
            address = item.get('Address', '')
            
            text_object.textLine(name)
            
            # Simple address wrapping/handling
            # Assuming address might be "123 Main St, Tioga PA" or just "123 Main St"
            # In a real scenario, you might split lines. Here we just print it.
            text_object.textLine(address)
            # Add city/state/zip if not in address field or if needed separately
            # based on how export-labels works. Currently it puts full address in 'Address'.
            
            c.drawText(text_object)

            # Move to next position
            col += 1
            if col >= self.labels_across:
                col = 0
                row += 1
            
            if row >= self.labels_down:
                c.showPage() # New page
                col = 0
                row = 0

        c.save()
        print(f"✅ Label PDF created: {output_filename}")
        return output_filename

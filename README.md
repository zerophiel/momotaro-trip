# Momotaro Trip - Sales Report Generator

[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful Python script to automatically generate professional PDF reports from sales transaction data. This tool processes raw text input files and generates three comprehensive reports: billing reports, top spender analysis, and top item popularity analysis.

## 📋 Table of Contents

- [Features](#-features)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Usage](#-usage)
- [Input Format](#-input-format)
- [Output Reports](#-output-reports)
- [Configuration](#-configuration)
- [Contributing](#-contributing)
- [Repository Setup](#-repository-setup)
- [Author](#-author)
- [License](#-license)

## ✨ Features

- **Automated PDF Generation**: Generate three professional PDF reports with a single command
- **Flexible Price Parsing**: Supports multiple price formats (rb, jt, standard numbers)
- **Smart Customer Matching**: Intelligent customer identification using phone numbers and names
- **Unicode Support**: Handles various Unicode characters and special formatting
- **Alphabetical Sorting**: Customer reports are automatically sorted alphabetically
- **Quantity Calculation**: Automatically counts item quantities based on repeated entries
- **Professional Formatting**: Clean, readable PDF layouts with proper styling

## 🚀 Installation

### Prerequisites

- Python 3.6 or higher
- pip (Python package installer)

### Step 1: Clone the Repository

```bash
git clone git@github.com:zerophiel/momotaro-trip.git
cd momotaro-trip
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install the required package:
- `reportlab>=4.0.0` - PDF generation library

## 🎯 Quick Start

1. **Prepare your input file**: Place your transaction data in `input-file.txt` (see [Input Format](#input-format) for details)

2. **Run the script**:
   ```bash
   python generate_reports.py
   ```
   
   Or use the batch file (Windows):
   ```bash
   run_script.bat
   ```

3. **Get your reports**: Three PDF files will be generated in the same directory:
   - `laporan_penagihan.pdf` - Detailed billing report per customer
   - `laporan_top_spender.pdf` - Top 5 customers by spending
   - `laporan_top_item.pdf` - Top 5 most popular items

## 📖 Usage

### Basic Usage

```bash
python generate_reports.py
```

The script will:
1. Read data from `input-file.txt`
2. Parse items, prices, and customer information
3. Generate three PDF reports
4. Display success messages for each generated report

### Input File Location

By default, the script looks for `input-file.txt` in the same directory. Make sure the file exists before running the script.

**⚠️ Privacy Note**: The `input-file.txt` file is not tracked by git by default. If you need to commit a sample file for testing, ensure all customer names and phone numbers are masked/anonymized.

## 📝 Input Format

### Item Format

Each item should be on its own line, followed by its price:

```
Product A 125rb
Product B 195rb
Product C isi 44 pcs 285rb
```

### Customer Format

Customers are indicated with checkboxes. Only items marked with `[x]` will be billed:

```
- [x] Customer A +62 812-XXXX-XXXX
- [x] Customer B +62 812-XXXX-XXXX
- [ ] Customer C +62 812-XXXX-XXXX  (not billed)
```

Alternative formats are also supported:
```
1. Customer Name +62 812-XXXX-XXXX
2. Another Customer +62 812-XXXX-XXXX
```

### Price Formats Supported

The script supports various price formats:

| Format | Example | Value |
|--------|---------|-------|
| Ribu (rb) | `125rb` | 125.000 |
| Juta (jt) | `3,4jt` | 3.400.000 |
| Standard | `1.989.000` | 1.989.000 |
| Mixed | `Product name 285rb additional info` | 285.000 (first price found) |

**Note**: If multiple prices appear in an item name, the first valid price will be used.

### Special Sections

Any content under "Product REQUEST cek harga" section will be ignored and not included in the reports.

### Customer Identification

- **With Phone Number**: Customers with identical phone numbers (normalized) are considered the same person
- **Without Phone Number**: Customers are matched by name (case-insensitive)
- **Phone Normalization**: 
  - `+62` and `0` prefixes are treated as equivalent
  - `08XXXXXXXXXX` and `+62 XXX-XXXX-XXXX` are considered the same customer

### Quantity Calculation

If a customer appears multiple times for the same item, the quantity is automatically incremented:

```
- [x] Customer A +62 812-XXXX-XXXX
- [x] Customer A +62 812-XXXX-XXXX
```
This will result in quantity = 2 for Customer A.

## 📊 Output Reports

### 1. Laporan Penagihan (`laporan_penagihan.pdf`)

A detailed billing report with:
- **Customer Information**: Name and phone number (if available) as table headers
- **Item Details**: Item name, quantity, unit price, and subtotal
- **Grand Total**: Total amount per customer
- **Organization**: Customers sorted alphabetically by name
- **Pagination**: Page numbers in bottom-right corner

**Features**:
- Each customer has a separate table with clear spacing
- Professional table styling with alternating row colors
- Bold formatting for grand totals

### 2. Laporan Top Spender (`laporan_top_spender.pdf`)

Shows the top 5 customers ranked by total spending:
- Customer name
- Phone number
- Total purchase amount

### 3. Laporan Top Item (`laporan_top_item.pdf`)

Shows the top 5 most popular items ranked by total quantity sold:
- Item name
- Total quantity sold
- Unit price
- Total revenue

## ⚙️ Configuration

### Customizing Output

You can modify the script to customize:
- **Page size**: Currently set to A4
- **Table styling**: Colors, fonts, and spacing
- **Currency format**: Currently `Rp. XXX.XXX,-`
- **Top N items**: Currently shows top 5 (can be changed in code)

### File Paths

To change input/output file paths, modify these variables in `generate_reports.py`:

```python
INPUT_FILE = 'input-file.txt'
BILLING_REPORT = 'laporan_penagihan.pdf'
TOP_SPENDER_REPORT = 'laporan_top_spender.pdf'
TOP_ITEM_REPORT = 'laporan_top_item.pdf'
```

## 🤝 Contributing

Contributions are welcome! This project is open to improvements and new features. Here's how you can contribute:

### How to Contribute

1. **Fork the repository**
   ```bash
   git clone git@github.com:zerophiel/momotaro-trip.git
   cd momotaro-trip
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Follow Python PEP 8 style guidelines
   - Add comments for complex logic
   - Test your changes thoroughly

4. **Commit your changes**
   ```bash
   git commit -m "Add: description of your feature"
   ```

5. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**
   - Provide a clear description of your changes
   - Reference any related issues

### Areas for Contribution

- 🐛 **Bug Fixes**: Report and fix bugs
- ✨ **New Features**: Add new report types or analysis
- 📚 **Documentation**: Improve documentation and examples
- 🎨 **UI/UX**: Enhance PDF formatting and styling
- ⚡ **Performance**: Optimize parsing and generation speed
- 🌐 **Internationalization**: Add support for other languages/currencies

### Code Style

- Use Python 3.6+ features
- Follow PEP 8 style guide
- Add docstrings for functions
- Use meaningful variable names
- Comment complex logic

## 🔧 Repository Setup

### Git Remote Configuration

If you're setting up the repository for the first time:

```bash
# Add remote repository
git remote add origin git@github.com:zerophiel/momotaro-trip.git

# Verify remote
git remote -v
```

You should see:
```
origin  git@github.com:zerophiel/momotaro-trip.git (fetch)
origin  git@github.com:zerophiel/momotaro-trip.git (push)
```

### Important: Files Not Tracked by Git

The following files are excluded from version control (see `.gitignore`):
- `*.pdf` - All PDF output files
- `input-file.txt` - Input file containing customer data (sensitive)

**Never commit these files** to protect customer privacy.

### Verify .gitignore is Working

After cloning or pulling, verify that sensitive files are ignored:

```bash
git status
```

You should **NOT** see PDF files or `input-file.txt` in the untracked files list.

### If You Accidentally Staged Sensitive Files

If you've already run `git add .` including PDF or input files:

```bash
# Unstage all files
git reset HEAD

# Add only the source files
git add generate_reports.py requirements.txt README.md .gitignore run_script.bat
```

## 👤 Author

**Danuarta Wiratama**

- Email: [danuarta.wiratama@gmail.com](mailto:danuarta.wiratama@gmail.com)
- GitHub: [@zerophiel](https://github.com/zerophiel)

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [ReportLab](https://www.reportlab.com/) for PDF generation
- Thanks to all contributors who help improve this project

## 🔒 Privacy & Data Security

**Important**: This script processes customer data including names and phone numbers. 

### Data Privacy Guidelines

- **Never commit sensitive data**: Do not commit `input-file.txt` files containing real customer information to the repository
- **Use sample data**: When contributing or testing, use anonymized sample data
- **Mask personal information**: All examples in documentation use masked data (e.g., `+62 XXX-XXXX-XXXX`, `Customer A`)
- **Local processing only**: The script runs locally on your machine - no data is sent to external servers

### Example Input File Format

When creating sample input files for testing or documentation, always use masked data:

```
Product A 125rb
- [x] Customer A +62 XXX-XXXX-XXXX
- [x] Customer B +62 XXX-XXXX-XXXX
```

**⚠️ Warning**: Never share or commit files containing real customer names, phone numbers, or transaction data.

## 📞 Support

If you encounter any issues or have questions:

1. Check the [Issues](https://github.com/zerophiel/momotaro-trip/issues) page
2. Create a new issue with detailed information
3. Contact the author at danuarta.wiratama@gmail.com

---

**Made with ❤️ for efficient sales reporting**

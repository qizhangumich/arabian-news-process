# Weekly Middle East Investment News Summarizer

This script fetches news from Firebase from a specified date range (default: past 7 days) and uses OpenAI's GPT-4 to generate a summary of investment-related news, specifically focusing on sovereign wealth funds and pension funds from the Middle East.

## Firebase Data Structure

The script targets the "arabian-business-news" Firebase project and expects news data with the following structure:

- Collection: `articles` (default, can be changed with `--collection` parameter)
- Document fields:
  - `date_publish` (primary date field used)
  - Alternatively: `date_published`, `published_date`, `publishedDate`, `date`, or `timestamp`
  - The date should be in ISO 8601 format (e.g., "2025-03-13T19:11:50+04:00")
  - `title`: Article title
  - `content`: Article content
  - `source`: Source of the article

The script automatically detects and uses the appropriate date field in the documents.

## Entities of Interest

The script specifically filters for news related to:
- Mubadala
- ADIA (Abu Dhabi Investment Authority)
- ADIC (Abu Dhabi Investment Council)
- PIF (Public Investment Fund)
- QIA (Qatar Investment Authority)
- OIA (Oman Investment Authority)
- Pension funds

## Prerequisites

Before running this script, ensure you have:
1. Python 3.7 or higher installed
2. A valid Firebase service account key (firebase_key.json) with access to the arabian-business-news project
3. An OpenAI API key (stored in key_for_openai.txt)

## Installation

1. Clone this repository or download the files.
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

1. Make sure that `firebase_key.json` is in the root directory.
2. Make sure that `key_for_openai.txt` containing your OpenAI API key is in the root directory.

## Usage

### Basic Usage

Run the script with default settings (last 7 days, 'articles' collection):

```bash
python weekly_news_summarizer.py
```

### Specifying Date Range

You can specify a custom date range using command-line arguments:

```bash
python weekly_news_summarizer.py --year 2025 --month 3 --start-day 7 --end-day 14
```

### Specifying Collection

To query a specific collection in the Firebase database:

```bash
python weekly_news_summarizer.py --collection articles
```

### Command-line Arguments

The script supports the following command-line arguments:

- `--year`: Year for the date range (default: current year)
- `--month`: Month to retrieve news from (default: 3 for March)
- `--start-day`: Start day of the month (default: 7)
- `--end-day`: End day of the month (default: 14)
- `--markdown`: Output the summary in Markdown format (default: plain text)
- `--collection`: Firebase collection to query (default: 'articles')

For example, to get news from April 1-10, 2025 in Markdown format from the 'news_articles' collection:

```bash
python weekly_news_summarizer.py --year 2025 --month 4 --start-day 1 --end-day 10 --markdown --collection news_articles
```

## Output

The script will:
1. Fetch news from Firebase for the specified date range
2. Print statistics about the date fields used in the documents
3. Filter for investment-related news mentioning the specified entities
4. Use OpenAI to generate a comprehensive summary
5. Print the summary to the console
6. Save the summary to a file named `investment_news_summary_COLLECTION_YYYY_MM_DD_to_MM_DD.txt` or `.md`

## Troubleshooting

- If you encounter any Firebase connection issues, ensure your `firebase_key.json` is valid and has the correct permissions.
- If you encounter OpenAI API issues, verify your API key is correct and has sufficient quota.
- If no documents are found in the date range, the script will show diagnostics with the earliest and latest dates found in the collection.
- Make sure the collection you're querying exists in the Firebase database.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
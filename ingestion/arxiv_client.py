import time
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from datetime import datetime, timezone
import requests
from config import settings


class ArxivClient:
    """Client for fetching papers from the arXiv API."""

    NAMESPACES = {
        'atom': 'http://www.w3.org/2005/Atom',
        'arxiv': 'http://arxiv.org/schemas/atom'
    }

    def __init__(self):
        self.base_url = settings.arxiv_base_url
        self.max_results = settings.max_results

    def build_query(
        self,
        categories: List[str] = None,
        keywords: List[str] = None,
        start_date: Optional[str] = None
    ) -> str:
        """
        Build arXiv API query string.

        Args:
            categories: List of arXiv categories (e.g., ['cs.RO', 'cs.CV', 'cs.LG'])
            keywords: Keywords to search in title/abstract (e.g., ['VLA', 'VLM', 'humanoid'])
            start_date: Start date in YYYYMMDD format (optional)

        Returns:
            Query string for arXiv API
        """
        if categories is None:
            categories = ['cs.RO', 'cs.CV', 'cs.LG', 'cs.AI']

        if keywords is None:
            keywords = ['VLA', 'VLM', 'humanoid', 'vision language action',
                       'vision language model', 'embodied AI', 'robot learning']

        category_query = ' OR '.join([f'cat:{cat}' for cat in categories])

        keyword_query = ' OR '.join([
            f'(ti:"{kw}" OR abs:"{kw}")' for kw in keywords
        ])

        query = f'({category_query}) AND ({keyword_query})'

        return query

    def fetch_papers(
        self,
        query: Optional[str] = None,
        max_results: Optional[int] = None,
        start: int = 0
    ) -> List[Dict]:
        """
        Fetch papers from arXiv API.

        Args:
            query: Custom query string (if None, uses default VLA/VLM/humanoid query)
            max_results: Maximum number of results to fetch
            start: Starting index for pagination

        Returns:
            List of paper dictionaries with metadata
        """
        if query is None:
            query = self.build_query()

        if max_results is None:
            max_results = self.max_results

        params = {
            'search_query': query,
            'start': start,
            'max_results': max_results,
            'sortBy': 'submittedDate',
            'sortOrder': 'descending'
        }

        print(f"Fetching papers from arXiv API...")
        print(f"Query: {query}")
        print(f"Max results: {max_results}")

        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()

            time.sleep(3)

            papers = self._parse_response(response.text)
            print(f"Successfully fetched {len(papers)} papers")

            return papers

        except requests.RequestException as e:
            print(f"Error fetching papers from arXiv: {e}")
            raise

    def _parse_response(self, xml_text: str) -> List[Dict]:
        """
        Parse arXiv API XML response.

        Args:
            xml_text: Raw XML response from arXiv API

        Returns:
            List of parsed paper dictionaries
        """
        root = ET.fromstring(xml_text)
        papers = []

        for entry in root.findall('atom:entry', self.NAMESPACES):
            try:
                paper = self._parse_entry(entry)
                papers.append(paper)
            except Exception as e:
                print(f"Error parsing entry: {e}")
                continue

        return papers

    def _parse_entry(self, entry: ET.Element) -> Dict:
        """Parse a single arXiv entry XML element."""

        id_elem = entry.find('atom:id', self.NAMESPACES)
        arxiv_id = id_elem.text.split('/')[-1] if id_elem is not None else None

        title_elem = entry.find('atom:title', self.NAMESPACES)
        title = title_elem.text.strip().replace('\n', ' ') if title_elem is not None else None

        summary_elem = entry.find('atom:summary', self.NAMESPACES)
        abstract = summary_elem.text.strip().replace('\n', ' ') if summary_elem is not None else None

        authors = []
        for author in entry.findall('atom:author', self.NAMESPACES):
            name_elem = author.find('atom:name', self.NAMESPACES)
            if name_elem is not None:
                authors.append(name_elem.text)

        published_elem = entry.find('atom:published', self.NAMESPACES)
        published_date = None
        if published_elem is not None:
            try:
                published_date = datetime.fromisoformat(
                    published_elem.text.replace('Z', '+00:00')
                )
            except ValueError:
                pass

        updated_elem = entry.find('atom:updated', self.NAMESPACES)
        updated_date = None
        if updated_elem is not None:
            try:
                updated_date = datetime.fromisoformat(
                    updated_elem.text.replace('Z', '+00:00')
                )
            except ValueError:
                pass

        categories = []
        for category in entry.findall('arxiv:primary_category', self.NAMESPACES):
            term = category.get('term')
            if term:
                categories.append(term)

        for category in entry.findall('atom:category', self.NAMESPACES):
            term = category.get('term')
            if term and term not in categories:
                categories.append(term)

        pdf_link = None
        for link in entry.findall('atom:link', self.NAMESPACES):
            if link.get('type') == 'application/pdf':
                pdf_link = link.get('href')
                break

        return {
            'arxiv_id': arxiv_id,
            'title': title,
            'abstract': abstract,
            'authors': authors,
            'published_date': published_date,
            'updated_date': updated_date,
            'categories': categories,
            'pdf_url': pdf_link,
            'ingested_at': datetime.now(timezone.utc)
        }

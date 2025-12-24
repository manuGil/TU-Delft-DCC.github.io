"""
Quarto Parser Module
"""
import re
import yaml
from pathlib import Path
from typing import List, Dict, Tuple


class QuartoParser:
    def __init__(self, docs_path: str):
        self.docs_path = Path(docs_path)

    def extract_yaml_frontmatter(self, content: str) -> Tuple[Dict, str] :
        """Extract YAML frontmatter from Quarto content."""
        
        pattern = r'^---\n(.*?)\n---\n(.*)$'
        match = re.match(pattern, content, re.DOTALL)
        if match:
            try:
                frontmatter = yaml.safe_load(match.group(1))
                body = match.group(2)
                return frontmatter, body
            except yaml.YAMLError:
                return {}, content
        return {}, content
    
    def split_by_headers(self, content: str) -> List[Dict[str, str]]:
        """Split content into chunks by headers."""
        sections = []
        current_section = {"header": "",
                           "level": 0,
                           "content": []}
        
        lines = content.split('\n')

        for line in lines:
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)

            if header_match:
                if current_section["content"]:
                    sections.append({
                        "header": current_section["header"],
                        "level": current_section["level"],
                        "content": '\n'.join(current_section["content"]).strip()
                    })

                    # Start a new section
                    current_section = {"header": header_match.group(2),
                                       "level": len(header_match.group(1)),
                                       "content": []}
            else:
                current_section["content"].append(line)

        # Add the last section 
        if current_section["content"]:
            sections.append({
                "header": current_section["header"],
                "level": current_section["level"],
                "content": '\n'.join(current_section["content"]).strip()
            })

        return sections
    
    def parse_file(self, filepath: Path) -> List[Dict]:
        """Parse a single Quarto file into chunks."""

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        frontmatter, body = self.extract_yaml_frontmatter(content)
        sections = self.split_by_headers(body)
        
        chunks = []
        for i, section in enumerate(sections):
            if not section["content"].strip():
                continue

            chunk = {
                "file": str(filepath.relative_to(self.docs_path)),
                "title": frontmatter.get("title", filepath.stem),
                "section_header": section["header"],
                "section_level": section["level"],
                "content": section["content"],
                "chunk_id": f"{filepath.stem}_{i}",
                "metadata": frontmatter
            }
            chunks.append(chunk)

        return chunks
    def parse_all_files(self) -> List[Dict]:
        """Parse all .qmd files in the documentation directory."""

        all_chunks = []
        excluded_dirs = {'_archived', 'img'}
        
        for filepath in self.docs_path.rglob('*.qmd'):
            
            # skip files in excluded directories
            if any(part.startswith('.') or part.startswith('_') or part in excluded_dirs for part in filepath.parts):
                continue
            print(f"Parsing file: {filepath}")
            chunks = self.parse_file(filepath)

            all_chunks.extend(chunks)
        return all_chunks
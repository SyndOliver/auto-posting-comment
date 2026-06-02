"""SKU to Shopee Affiliate Link mapping manager.

Reads SKU → affiliate link mappings from a CSV file and provides
lookup functionality. Supports multiple shops/pages with separate
affiliate links per SKU (affiliate_link_1, affiliate_link_2, etc.).
"""

import csv
import os
from dataclasses import dataclass, field

from src.utils.logger import setup_logger

logger = setup_logger("sku_manager")


@dataclass
class ProductInfo:
    """Product information from SKU mapping.

    affiliate_links is a list where index 0 = Page 1's link,
    index 1 = Page 2's link, etc. Maps to FB_PAGE1, FB_PAGE2
    order in .env config.
    """

    sku: str
    affiliate_links: list[str] = field(default_factory=list)
    product_name: str = ""

    def get_link(self, page_index: int) -> str:
        """Get affiliate link for a specific page.

        Args:
            page_index: 0-based index matching the page order in config.

        Returns:
            The affiliate link for that page, or the first link as fallback.
        """
        if page_index < len(self.affiliate_links):
            return self.affiliate_links[page_index]
        # Fallback to first link if index out of range
        return self.affiliate_links[0] if self.affiliate_links else ""


class SKUManager:
    """Manages SKU to affiliate link mappings.

    Loads data from a CSV file with columns:
        sku, affiliate_link_1, affiliate_link_2, ..., product_name

    Each affiliate_link_N column maps to the Nth Facebook Page
    configured in .env (FB_PAGE1, FB_PAGE2, etc.).
    """

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self._mapping: dict[str, ProductInfo] = {}
        self.load()

    def load(self) -> int:
        """Load or reload SKU mappings from CSV file.

        Returns:
            Number of SKUs loaded.

        Raises:
            FileNotFoundError: If CSV file doesn't exist.
        """
        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(
                f"SKU mapping file not found: {self.csv_path}"
            )

        self._mapping.clear()

        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            # Validate required columns
            if reader.fieldnames is None:
                raise ValueError("CSV file is empty or has no headers")

            actual_cols = [col.strip().lower() for col in reader.fieldnames]

            if "sku" not in actual_cols:
                raise ValueError("CSV missing required column: sku")
            if "product_name" not in actual_cols:
                raise ValueError("CSV missing required column: product_name")

            # Find all affiliate_link columns (affiliate_link_1, affiliate_link_2, ...)
            link_cols = sorted(
                [c for c in actual_cols if c.startswith("affiliate_link")],
            )
            if not link_cols:
                raise ValueError(
                    "CSV missing affiliate link columns. "
                    "Expected: affiliate_link_1, affiliate_link_2, ..."
                )

            logger.info("Found %d affiliate link columns: %s", len(link_cols), link_cols)

            for row in reader:
                sku = row.get("sku", "").strip().upper()
                product_name = row.get("product_name", "").strip()

                if not sku:
                    logger.warning("Skipping row with empty SKU: %s", row)
                    continue

                # Collect affiliate links in order
                affiliate_links = []
                for col in link_cols:
                    link = row.get(col, "").strip()
                    affiliate_links.append(link)

                if not any(affiliate_links):
                    logger.warning(
                        "Skipping SKU %s: no affiliate links found", sku
                    )
                    continue

                self._mapping[sku] = ProductInfo(
                    sku=sku,
                    affiliate_links=affiliate_links,
                    product_name=product_name,
                )

        logger.info(
            "Loaded %d SKU mappings from %s",
            len(self._mapping),
            self.csv_path,
        )
        return len(self._mapping)

    def lookup(self, sku: str) -> ProductInfo | None:
        """Look up product info by SKU.

        Args:
            sku: The SKU to look up (case-insensitive).

        Returns:
            ProductInfo if found, None otherwise.
        """
        return self._mapping.get(sku.strip().upper())

    def get_all_skus(self) -> list[ProductInfo]:
        """Get all loaded SKU mappings.

        Returns:
            List of all ProductInfo objects, sorted by SKU.
        """
        return sorted(self._mapping.values(), key=lambda p: p.sku)

    @property
    def count(self) -> int:
        """Return the number of loaded SKUs."""
        return len(self._mapping)

    def format_comment(self, product: ProductInfo, page_index: int = 0) -> str:
        """Format the comment message for a product on a specific page.

        Args:
            product: The product info.
            page_index: 0-based index of the page (maps to affiliate_link_N).

        Returns:
            Formatted comment string with the correct affiliate link.
        """
        link = product.get_link(page_index)
        return (
            f"🛒 {product.product_name}\n"
            f"👉 Mua ngay: {link}"
        )

"""SKU to Shopee Affiliate Link mapping manager.

Reads SKU → affiliate link mappings from a CSV file and provides
lookup functionality.
"""

import csv
import os
from dataclasses import dataclass

from src.utils.logger import setup_logger

logger = setup_logger("sku_manager")


@dataclass
class ProductInfo:
    """Product information from SKU mapping."""

    sku: str
    affiliate_link: str
    product_name: str


class SKUManager:
    """Manages SKU to affiliate link mappings.

    Loads data from a CSV file with columns: sku, affiliate_link, product_name
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

            required_cols = {"sku", "affiliate_link", "product_name"}
            actual_cols = {col.strip().lower() for col in reader.fieldnames}
            missing = required_cols - actual_cols
            if missing:
                raise ValueError(
                    f"CSV missing required columns: {missing}. "
                    f"Expected: sku, affiliate_link, product_name"
                )

            for row in reader:
                sku = row.get("sku", "").strip().upper()
                affiliate_link = row.get("affiliate_link", "").strip()
                product_name = row.get("product_name", "").strip()

                if not sku or not affiliate_link:
                    logger.warning(
                        "Skipping row with empty SKU or link: %s", row
                    )
                    continue

                self._mapping[sku] = ProductInfo(
                    sku=sku,
                    affiliate_link=affiliate_link,
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

    def format_comment(self, product: ProductInfo) -> str:
        """Format the comment message for a product.

        Args:
            product: The product info.

        Returns:
            Formatted comment string with affiliate link.
        """
        return (
            f"🛒 {product.product_name}\n"
            f"👉 Mua ngay: {product.affiliate_link}"
        )

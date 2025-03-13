"""Helper functions for Selenium operations."""

import logging
import time
from typing import Optional, List, Tuple, Any

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
)

logger = logging.getLogger(__name__)


def wait_for_element(
    driver: webdriver.Chrome,
    by: By,
    value: str,
    timeout: int = 10,
    condition: str = "presence",
) -> Any:
    """Wait for an element to be in the specified condition.

    Args:
        driver: WebDriver instance
        by: Method to locate element (e.g., By.ID)
        value: The value to search for
        timeout: Wait timeout in seconds
        condition: The element condition to wait for
                  (presence, visibility, clickable)

    Returns:
        The found WebElement

    Raises:
        TimeoutException: If element doesn't meet the condition within timeout
    """
    wait = WebDriverWait(driver, timeout)

    if condition == "presence":
        return wait.until(EC.presence_of_element_located((by, value)))
    elif condition == "visibility":
        return wait.until(EC.visibility_of_element_located((by, value)))
    elif condition == "clickable":
        return wait.until(EC.element_to_be_clickable((by, value)))
    else:
        raise ValueError(f"Unknown wait condition: {condition}")


def safe_click(driver: webdriver.Chrome, element, max_attempts: int = 3) -> bool:
    """Safely click an element, handling common exceptions.

    Args:
        driver: WebDriver instance
        element: Element to click
        max_attempts: Maximum number of click attempts

    Returns:
        True if click succeeded, False otherwise
    """
    for attempt in range(max_attempts):
        try:
            # Scroll to element
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", element
            )
            time.sleep(0.5)  # Allow time for scrolling

            # Try regular click first
            element.click()
            return True

        except ElementClickInterceptedException:
            logger.warning(
                f"Click intercepted, trying JavaScript click (attempt {attempt + 1})"
            )
            try:
                # Try JavaScript click as fallback
                driver.execute_script("arguments[0].click();", element)
                return True
            except Exception as js_error:
                logger.warning(f"JavaScript click failed: {str(js_error)}")

        except StaleElementReferenceException:
            logger.warning(f"Stale element reference (attempt {attempt + 1})")
            # Element is stale, need to find it again
            return False

        except Exception as e:
            logger.warning(f"Click failed: {str(e)} (attempt {attempt + 1})")

        # Wait before retrying
        time.sleep(1)

    return False


def extract_table_data(
    driver: webdriver.Chrome, table_selector: str, header_row: bool = True
) -> List[List[str]]:
    """Extract data from a table into a list of rows.

    Args:
        driver: WebDriver instance
        table_selector: CSS selector for the table
        header_row: Whether the table has a header row

    Returns:
        List of rows, where each row is a list of cell text values
    """
    try:
        # Wait for table to be present
        wait_for_element(driver, By.CSS_SELECTOR, table_selector)

        # Get all rows
        rows = driver.find_elements(By.CSS_SELECTOR, f"{table_selector} tr")

        # Extract data from rows
        table_data = []
        start_row = 1 if header_row else 0

        # Extract headers if present
        if header_row and rows:
            headers = [
                th.text.strip() for th in rows[0].find_elements(By.TAG_NAME, "th")
            ]
            table_data.append(headers)

        # Extract data rows
        for row in rows[start_row:]:
            # Get cells (can be th or td)
            cells = row.find_elements(By.TAG_NAME, "td")
            if not cells:
                cells = row.find_elements(By.TAG_NAME, "th")

            row_data = [cell.text.strip() for cell in cells]
            table_data.append(row_data)

        return table_data

    except Exception as e:
        logger.error(f"Error extracting table data: {str(e)}")
        return []


def scroll_to_bottom(driver: webdriver.Chrome, scroll_pause_time: float = 1.0) -> None:
    """Scroll to the bottom of the page incrementally.

    Args:
        driver: WebDriver instance
        scroll_pause_time: Time to pause between scrolls
    """
    # Get scroll height
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Wait to load page
        time.sleep(scroll_pause_time)

        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            # If heights are the same, we've reached the bottom
            break
        last_height = new_height

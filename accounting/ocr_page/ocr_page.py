"""
OCR Page abstract base class.
Provides OCR capabilities for any page class that inherits from it.
Follows the same pattern as WorkPage for work entities.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import datetime as dt
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.gateway import get_gateway
from hh.deploy.deploy_utils import detect_project_context
from hh_page.page import Page
from hh_page.page_registry import get_page
from hh_page.page_class_registry import register_page_class

def _format_relative_time(timestamp_str: str) -> str:
    """Convert ISO timestamp to relative time string (e.g., '3 days ago')."""
    trace_in()
    try:
        if not timestamp_str:
            trace_out()
            return ''
        # Parse ISO timestamp
        timestamp = dt.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = dt.datetime.now(timestamp.tzinfo if timestamp.tzinfo else None)
        delta = now - timestamp

        # Calculate time differences
        seconds = int(delta.total_seconds())
        if seconds < 60:
            result = 'just now' if seconds < 10 else f'{seconds} seconds ago'
        elif seconds < 3600:
            minutes = seconds // 60
            result = '1 minute ago' if minutes == 1 else f'{minutes} minutes ago'
        elif seconds < 86400:
            hours = seconds // 3600
            result = '1 hour ago' if hours == 1 else f'{hours} hours ago'
        elif seconds < 604800:
            days = seconds // 86400
            result = '1 day ago' if days == 1 else f'{days} days ago'
        elif seconds < 2592000:
            weeks = seconds // 604800
            result = '1 week ago' if weeks == 1 else f'{weeks} weeks ago'
        elif seconds < 31536000:
            months = seconds // 2592000
            result = '1 month ago' if months == 1 else f'{months} months ago'
        else:
            years = seconds // 31536000
            result = '1 year ago' if years == 1 else f'{years} years ago'
        log(f"Converted timestamp '{timestamp_str}' to '{result}'")
        trace_out()
        return result
    except Exception as e:
        warn(f"Error formatting relative time for '{timestamp_str}': {e}")
        trace_out()
        return timestamp_str

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_ocr_page_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_page_class('ocrPage')
class OcrPage(Page):
    """
    Abstract base class for pages with OCR capabilities.
    Provides OCR functionality similar to how WorkPage provides work entity functionality.
    This class should never be instantiated directly - only inherited from.
    """

    # Type annotations for metadata-extracted attributes
    ocr_status: Optional[str]

    def __init__(self, id: int):
        """Initialize OcrPage by calling parent constructor."""
        super().__init__(id)

    def _after_metadata_extraction(self) -> None:
        """Override hook to set defaults for OCR metadata fields and trigger recalculation if needed."""
        # Initialize metadata-extracted attributes with defaults
        if not hasattr(self, 'ocr_status'):
            self.ocr_status = None

        # Call parent hook for proper chaining
        super()._after_metadata_extraction()

    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        """OcrPage is abstract - never allow it to be created directly."""
        return False

    def check_has_images(self) -> bool:
        """
        Check if this page has any attached images.
        Returns True if images exist, False otherwise.
        """
        trace_in(f"Checking for images on page {self.id}")
        has_images = len(self.get_images_data()) > 0
        log(f"Page {self.id} has images: {has_images}")
        trace_out()
        return has_images


    def perform_ocr_on_image(self, image_path: Path) -> Tuple[str, str, List[float]]:
        """
        Perform OCR on a single image file.
        Returns tuple of (extracted_text, timestamp, confidence_scores)
        """
        trace_in(f"Performing OCR on {image_path}")
        try:
            import easyocr  # type: ignore
            log("Initializing EasyOCR reader")
            reader = easyocr.Reader(['en'])
            log("EasyOCR reader initialized successfully")

            log("Starting OCR text extraction")
            results = reader.readtext(str(image_path))
            log(f"OCR extraction completed, found {len(results)} text regions")

            # Combine all text results
            ocr_text = '\n'.join([result[1] for result in results])
            log(f"Combined OCR text length: {len(ocr_text)} characters")

            # Extract confidence scores
            confidence_scores = [result[2] for result in results if len(result) > 2]

            # Generate timestamp
            timestamp = dt.datetime.now().isoformat()

            log(f"OCR completed successfully with {len(confidence_scores)} confidence scores")
            trace_out()
            return ocr_text, timestamp, confidence_scores

        except Exception as e:
            error_msg = f"OCR processing failed: {str(e)}"
            warn(error_msg)
            report_error("action", error_msg)
            trace_out()
            return "", "", []

    def perform_batch_ocr(self) -> Dict[str, Dict[str, Any]]:
        """
        Perform OCR on all images attached to this page.
        Returns dictionary keyed by image_id with OCR results.
        All-or-nothing: if any image fails, the entire operation fails.
        """
        trace_in(f"Starting batch OCR for page {self.id}")

        # Get all images for this page using Page's cached method
        images_data = self.get_images_data()
        if not images_data:
            log(f"No images found for page {self.id}")
            trace_out()
            return {}

        ocr_results = {}
        failed_images = []

        # Process each image
        for image_data in images_data:
            image_id = str(image_data['id'])
            log(f"Processing image {image_id}")

            # Get image path (1500px preferred) from instances
            instances = image_data.get('instances', [])
            if not instances:
                warn(f"No instances found for image {image_id}")
                failed_images.append(image_id)
                continue

            # Find 1500px instance or largest available
            target_instance = None
            for instance in instances:
                if instance.get('width') == 1500:
                    target_instance = instance
                    break
            if not target_instance:
                # Fall back to largest instance
                target_instance = max(instances, key=lambda inst: inst.get('width', 0) * inst.get('height', 0))

            if not target_instance or not target_instance.get('src'):
                warn(f"No suitable instance found for image {image_id}")
                failed_images.append(image_id)
                continue

            # Construct full path
            project_name, _ = detect_project_context()
            base_path = Path(f"/srv/images/{project_name}")
            image_path = base_path / target_instance['src']

            if not image_path.exists():
                warn(f"Image file does not exist: {image_path}")
                failed_images.append(image_id)
                continue

            # Perform OCR
            ocr_text, timestamp, confidence_scores = self.perform_ocr_on_image(image_path)

            if is_error():
                # OCR failed for this image
                failed_images.append(image_id)
                continue

            # Store successful results
            confidence_str = ','.join([f"{score:.3f}" for score in confidence_scores])
            ocr_results[image_id] = {
                'text': ocr_text,
                'timestamp': timestamp,
                'confidence': confidence_str
            }

            log(f"Successfully processed image {image_id}")

        # Check for failures - all-or-nothing policy
        if failed_images:
            error_msg = f"OCR failed for images: {', '.join(failed_images)}"
            warn(error_msg)
            report_error("action", error_msg)
            trace_out()
            return {}

        log(f"Batch OCR completed successfully for {len(ocr_results)} images")
        trace_out()
        return ocr_results

    def update_ocr_metadata(self, ocr_results: Dict[str, Dict[str, Any]]) -> bool:
        """
        Update page metadata with OCR results.
        Stores ocr_text, ocr_timestamps, ocr_confidence, and ocr_status.
        """
        trace_in(f"Updating OCR metadata for page {self.id}")

        gateway = get_gateway()
        if not gateway or not gateway.conn:
            warn("Gateway or connection not available")
            trace_out()
            return False

        # Prepare metadata updates
        ocr_text = {}
        ocr_timestamps = {}
        ocr_confidence = {}

        for image_id, results in ocr_results.items():
            ocr_text[image_id] = results['text']
            ocr_timestamps[image_id] = results['timestamp']
            ocr_confidence[image_id] = results['confidence']

        # Get current metadata
        metadata = self._get_metadata_dict()

        # Update OCR metadata
        metadata['ocr_text'] = ocr_text
        metadata['ocr_timestamps'] = ocr_timestamps
        metadata['ocr_confidence'] = ocr_confidence
        metadata['ocr_status'] = 'success'

        # Save metadata
        if not self._write_metadata_dict(metadata):
            warn(f"Failed to update OCR metadata for page {self.id}")
            report_error("action", f"Failed to update OCR metadata")
            trace_out()
            return False

        # Flag page modification for cache refresh
        self.flag_page_modification("OCR completed")

        log(f"Successfully updated OCR metadata for page {self.id}")
        trace_out()
        return True

    def get_ocr_text(self, image_id: Optional[int] = None) -> Dict[str, str]:
        """Get OCR text results. If image_id specified, return text for that image only."""
        metadata = self._get_metadata_dict()
        ocr_text = metadata.get('ocr_text', {})

        if image_id is not None:
            image_id_str = str(image_id)
            return {image_id_str: ocr_text.get(image_id_str, '')}

        return ocr_text

    def get_ocr_timestamps(self, image_id: Optional[int] = None) -> Dict[str, str]:
        """Get OCR timestamps. If image_id specified, return timestamp for that image only."""
        metadata = self._get_metadata_dict()
        ocr_timestamps = metadata.get('ocr_timestamps', {})

        if image_id is not None:
            image_id_str = str(image_id)
            return {image_id_str: ocr_timestamps.get(image_id_str, '')}

        return ocr_timestamps

    def get_ocr_confidence(self, image_id: Optional[int] = None) -> Dict[str, str]:
        """Get OCR confidence scores. If image_id specified, return confidence for that image only."""
        metadata = self._get_metadata_dict()
        ocr_confidence = metadata.get('ocr_confidence', {})

        if image_id is not None:
            image_id_str = str(image_id)
            return {image_id_str: ocr_confidence.get(image_id_str, '')}

        return ocr_confidence

    def get_ocr_status(self) -> Optional[str]:
        """Get OCR processing status."""
        return getattr(self, 'ocr_status', None)

    def get_ocr_data(self) -> Dict[str, Any]:
        """Get all OCR data for this page."""
        return {
            'ocr_status': self.get_ocr_status(),
            'ocr_text': self.get_ocr_text(),
            'ocr_timestamps': self.get_ocr_timestamps(),
            'ocr_confidence': self.get_ocr_confidence()
        }

    @classmethod
    def _after_add_page(cls, new_page_id: int):
        """
        Hook called after page creation to initialize OCR metadata.
        Sets default values for OCR fields.
        """
        trace_in()
        gateway = get_gateway()
        if not gateway:
            warn("No gateway available for add_page_class_information")
            trace_out()
            return

        page = get_page(new_page_id)
        if not page:
            warn(f"Failed to load page {new_page_id} for metadata initialization")
            trace_out()
            return

        # Initialize OCR fields with defaults
        page.set_metadata_value('ocr_status', None)

        # Also set attributes directly
        page.ocr_status = None

        log(f"Initialized OCR metadata for page {new_page_id}")
        trace_out()

    def _add_badge_headers(self) -> Dict[str, Any]:
        """Override to add OCR-specific fields to badge headers."""
        trace_in()

        # Get base badge headers from parent
        badge_headers = super()._add_badge_headers()

        # Create OCR status summary badge
        ocr_status = self.get_ocr_status()
        ocr_data = self.get_ocr_data()

        # Always get ocr_text regardless of status (for variable scoping)
        ocr_text = ocr_data.get('ocr_text', {})
        ocr_timestamps = ocr_data.get('ocr_timestamps', {})
        ocr_confidence = ocr_data.get('ocr_confidence', {})

        if ocr_status:
            badge_data = {'ocr_status': ocr_status}

            # Add summary data as additional rows
            if ocr_text and len(ocr_text) > 0:
                badge_data['ocr_images_processed'] = str(len(ocr_text))

            if ocr_timestamps and len(ocr_timestamps) > 0:
                latest_timestamp = max(ocr_timestamps.values()) if ocr_timestamps else None
                if latest_timestamp:
                    relative_time = _format_relative_time(latest_timestamp)
                    badge_data['ocr_timestamps'] = relative_time

            if ocr_confidence and len(ocr_confidence) > 0:
                confidence_scores = []
                for conf_str in ocr_confidence.values():
                    try:
                        scores = [float(s) for s in conf_str.split(',') if s.strip()]
                        confidence_scores.extend(scores)
                    except (ValueError, TypeError):
                        continue

                if confidence_scores:
                    avg_confidence = sum(confidence_scores) / len(confidence_scores)
                    badge_data['ocr_confidence'] = f"{avg_confidence:.1f}%"

            badge_headers['ocr_status'] = badge_data

        # Create separate badge for EACH processed image showing its OCR text
        if ocr_text and len(ocr_text) > 0:
            for image_id, extracted_text in ocr_text.items():
                if extracted_text and extracted_text.strip():
                    badge_data = {'ocr_image_id': image_id}

                    # Add timestamp for this specific image
                    image_timestamp = ocr_timestamps.get(image_id, '')
                    if image_timestamp:
                        relative_time = _format_relative_time(image_timestamp)
                        badge_data['ocr_timestamp'] = relative_time

                    # Add confidence for this specific image
                    image_confidence = ocr_confidence.get(image_id, '')
                    if image_confidence:
                        # Calculate average confidence for this image's scores
                        try:
                            scores = [float(s) for s in image_confidence.split(',') if s.strip()]
                            if scores:
                                avg_confidence = sum(scores) / len(scores)
                                badge_data['ocr_confidence'] = f"{avg_confidence:.1f}%"
                        except (ValueError, TypeError):
                            badge_data['ocr_confidence'] = image_confidence

                    # Add the actual OCR text
                    badge_data['ocr_text'] = extracted_text

                    badge_headers[f'ocr_image_{image_id}'] = badge_data

        trace_out()
        return badge_headers

    def finalize_response_http(self, source_data: Dict[str, Any]) -> None:
        """OcrPage keeps page_summary badge even for HTTP backend."""
        pass  # Don't remove page_summary badge

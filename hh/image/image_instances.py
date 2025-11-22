from typing import Dict, Any, List, Optional
from pathlib import Path
from hh.gateway.connection.connection import r_query, u_query, c_query, d_query
from hh.gateway.connection.decorators import db_read, db_write
from hh.gateway.connection.types import DatabaseConnection
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.image.image_method_registry import register_image_mixin_methods

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_image_instances_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)

@register_image_mixin_methods
def _register_instances_methods():
    return {
        'load_instances': {'mixin_method': '_load_instances', 'decorator': 'read'},
        'get_instances': {'mixin_method': '_get_instances', 'decorator': 'read'},
        'get_instances_data': {'mixin_method': '_get_instances_data', 'decorator': 'read'},
        'get_best_instance': {'mixin_method': '_get_best_instance', 'decorator': 'read'},
        'add_image_instance': {'mixin_method': '_add_image_instance', 'decorator': 'write'},
        'copy_instances': {'mixin_method': '_copy_instances', 'decorator': 'write'},
        'process_upload': {'mixin_method': '_process_upload', 'decorator': 'write'},
    }

class ImageInstancesMixin:
    
    def _load_instances(self) -> List[Dict[str, Any]]:
        trace_in()
        instances = []
        if not is_error():
            try:
                query = "SELECT * FROM image_instances WHERE image_id = %s ORDER BY width DESC"
                results = r_query(self.conn, query, [self.id])
                for row in results:
                    instances.append({
                        'width': row['width'],
                        'height': row['height'],
                        'src': row['src'],
                        'filesize': row['filesize']
                    })
                log(f"Loaded {len(instances)} instances for image {self.id}")
            except Exception as e:
                warn(f"Failed to load instances for image {self.id}: {str(e)}")
                report_error("backend", f"Failed to load instances: {str(e)}")
        trace_out()
        return instances


    def _get_instances(self) -> List[Dict[str, Any]]:
        if not self.instances:  # Load on-demand if not already loaded
            self.instances = self._load_instances()
            # Flag that cache needs refresh since we just hydrated
            if self.instances:  # Only flag if actual instances were loaded
                self._flag_cache_refresh()
        return self.instances.copy()



    def _get_instances_data(self) -> List[Dict[str, Any]]:
        trace_in()
        instances_data = []
        if not is_error():
            for instance in self.instances:
                # Extract filename from src path
                from pathlib import Path
                src_path = instance.get('src', '')
                filename = Path(src_path).name if src_path else f"image_{self.id}_unknown"
                instance_data = {
                    'width': instance.get('width', 0),
                    'height': instance.get('height', 0),
                    'filesize': instance.get('filesize', 0),
                    'filename': filename,
                    'src': instance.get('src', '')
                }
                instances_data.append(instance_data)
            log(f"Prepared {len(instances_data)} instances for image {self.id}")
        trace_out()
        return instances_data


    def _get_best_instance(self, target_width: Optional[int] = None, target_height: Optional[int] = None) -> Optional[Dict[str, Any]]:
        trace_in()
        log(f"Finding best instance for image {self.id} (width={target_width}, height={target_height})")
        if not self.instances:
            log("No instances available")
            trace_out()
            return None
        if target_width is None and target_height is None:
            target_width = 300
        best = None
        if target_width:
            for instance in self.instances:
                if instance['width'] >= target_width:
                    if best is None or instance['width'] < best['width']:
                        best = instance
        elif target_height:
            for instance in self.instances:
                if instance['height'] >= target_height:
                    if best is None or instance['height'] < best['height']:
                        best = instance
        if best:
            log(f"Found best instance: {best['width']}x{best['height']}")
        else:
            log("No suitable instance found")
        trace_out()
        return best


    def _add_image_instance(self, width: int, height: int, src: str, filesize: int) -> bool:
        trace_in()
        log(f"Adding image instance for image {self.id}: {width}x{height}")
        if not is_error():
            new_id = c_query(self.conn, """
                INSERT INTO image_instances (image_id, width, height, src, filesize)
                VALUES (%s, %s, %s, %s, %s)
            """, (self.id, width, height, src, filesize))
            if new_id is not None:
                # Add to instances list
                self.instances.append({
                    'width': width,
                    'height': height,
                    'src': src,
                    'filesize': filesize
                })
                log(f"Successfully added image instance for image {self.id}")
            else:
                warn(f"Failed to add image instance for image {self.id}")
                report_error("action", f"Failed to add image instance for image {self.id}")
        trace_out()
        return not is_error()


    def _copy_instances(self, target_image) -> bool:
        trace_in()
        log(f"Copying instances from image {target_image.id} to image {self.id}")
        if not is_error():
            # Get instances from target image
            target_instances = target_image.get_instances()
            if not target_instances:
                warn(f"No instances found in target image {target_image.id}")
                report_error("action", f"No instances found in target image {target_image.id}")
                trace_out()
                return False
            # Copy each instance
            copied_count = 0
            for instance in target_instances:
                if not self.add_image_instance(instance['width'], instance['height'], instance['src'], instance['filesize']):
                    warn(f"Failed to copy instance: {instance['width']}x{instance['height']}")
                    report_error("action", f"Failed to copy instance: {instance['width']}x{instance['height']}")
                    trace_out()
                    return False
                copied_count += 1
            log(f"Successfully copied {copied_count} instances from image {target_image.id} to image {self.id}")
        trace_out()
        return not is_error()


    def _process_upload(self, uploaded_file_path: str, filename: str) -> bool:
        trace_in()
        log(f"Processing upload for image {self.id}: {uploaded_file_path}")
        if not is_error():
            instances_data = self._process_image(uploaded_file_path, filename)
            if not instances_data:
                warn("No image instances created")
                report_error("action", "Image processing failed")
                trace_out()
                return False
            # Save instances to database
            for instance_data in instances_data:
                if not self.add_image_instance(instance_data['width'], instance_data['height'], instance_data['src'], instance_data['filesize']):
                    trace_out()
                    return False
            log(f"Successfully processed {len(instances_data)} image instances")
        trace_out()
        return not is_error()


    def _process_image(self, source_file_path: str, filename_base: str) -> List[Dict[str, Any]]:
        trace_in()
        log(f"Starting image processing: {source_file_path} -> {filename_base}")
        try:
            from hh.image.utils import load_image, validate_image_size, create_date_directory
            from hh.image.image_size_tiers import IMAGE_SIZE_TIERS, MIN_IMAGE_WIDTH
            from pathlib import Path
            # Get base path for image storage
            try:
                from hh.deploy.utils import detect_project_context
                project_name, _ = detect_project_context()
                base_path = Path(f"/srv/images/{project_name}")
            except Exception as e:
                warn(f"Failed to detect project context: {e}")
                report_error("action", f"Failed to detect project context: {e}")
                trace_out()
                return []
            # Validate source file exists
            if not Path(source_file_path).exists():
                warn(f"Source file not found: {source_file_path}")
                report_error("action", f"Source file not found: {source_file_path}")
                log(f"Image processing FAILED: Source file not found - {source_file_path}")
                trace_out()
                return []
            # Load and validate image
            img = load_image(source_file_path)
            if not img:
                warn(f"Failed to load image: {source_file_path}")
                report_error("action", f"Failed to load image: {source_file_path}")
                log(f"Image processing FAILED: Could not load image - {source_file_path}")
                trace_out()
                return []
            # Validate minimum size requirements
            if not validate_image_size(img, min_width=MIN_IMAGE_WIDTH):
                warn(f"Image too small: {source_file_path}")
                report_error("action", f"Image too small: {source_file_path}")
                log(f"Image processing FAILED: Image too small - {source_file_path}")
                trace_out()
                return []
            # Create date-based directory structure
            try:
                date_path = create_date_directory(base_path)
                if not date_path:
                    warn(f"Failed to create date directory")
                    report_error("action", "Failed to create date directory")
                    log(f"Image processing FAILED: Could not create date directory - {base_path}")
                    trace_out()
                    return []
            except Exception as e:
                error_msg = str(e)
                warn(f"Failed to create date directory: {error_msg}")
                report_error("action", error_msg)
                log(f"Image processing FAILED: Could not create date directory - {base_path} - {error_msg}")
                trace_out()
                return []
            # Process image sizes - dynamic tier processing
            instances = []
            # 1. Always save full-size version first
            full_size_data = self._save_full_size(img, date_path, filename_base, base_path)
            if full_size_data:
                instances.append(full_size_data)
                log(f"Saved full-size image: {img.width}x{img.height}")
            # 2. Process each size tier dynamically
            size_tiers = IMAGE_SIZE_TIERS
            for tier_name, target_width in size_tiers.items():
                if not is_error():
                    # Only process if original is larger than target (prevent upsampling)
                    if img.width > target_width:
                        instance_data = self._process_size(img, tier_name, target_width, date_path, filename_base, base_path)
                        if instance_data:
                            instances.append(instance_data)
                            log(f"Created {tier_name} variant: {target_width}px (downsampled from {img.width}px)")
                    else:
                        log(f"Skipped {tier_name} variant: original {img.width}px <= target {target_width}px (no upsampling)")
            # Calculate total file size
            total_size = sum(instance['filesize'] for instance in instances)
            log(f"Image processing COMPLETED: {len(instances)} instances created, {total_size} bytes total, base_path={base_path}")
            trace_out()
            return instances
        except Exception as e:
            warn(f"Image processing failed: {str(e)}")
            report_error("action", f"Image processing failed: {str(e)}")
            log(f"Image processing FAILED: Unexpected error - {source_file_path} -> {str(e)}")
            trace_out()
            return []


    def _process_size(self, img, tier_name: str, target_width: int, date_path: Path, filename_base: str, base_path: Path) -> Optional[Dict[str, Any]]:
        trace_in()
        try:
            from hh.image.utils import calculate_target_height, scale_image, write_jpg
            # Calculate target dimensions
            target_height = calculate_target_height(img, target_width)
            # Scale image
            scaled_img = scale_image(img, target_width, target_height)
            if not scaled_img:
                log(f"Size processing FAILED: {tier_name} ({target_width}px) - scaling failed")
                trace_out()
                return None
            # Generate file path with tier name
            filepath = date_path / f"{filename_base}_{tier_name}.jpg"
            # Write image file
            if write_jpg(scaled_img, filepath, 80):  # Default quality
                result = {
                    'width': scaled_img.width,
                    'height': scaled_img.height,
                    'src': str(filepath.relative_to(base_path)),
                    'filesize': filepath.stat().st_size
                }
                log(f"Size processing SUCCESS: {tier_name} -> {scaled_img.width}x{scaled_img.height}, {result['filesize']} bytes, {result['src']}")
                trace_out()
                return result
            log(f"Size processing FAILED: {tier_name} ({target_width}px) - JPEG write failed")
            trace_out()
            return None
        except Exception as e:
            warn(f"Failed to process size {tier_name}: {str(e)}")
            log(f"Size processing FAILED: {tier_name} ({target_width}px) - {str(e)}")
            trace_out()
            return None


    def _save_full_size(self, img, date_path: Path, filename_base: str, base_path: Path) -> Optional[Dict[str, Any]]:
        trace_in()
        try:
            from hh.image.utils import write_jpg
            # Generate file path for full-size image
            filepath = date_path / f"{filename_base}.jpg"
            # Write original image as JPEG
            if write_jpg(img, filepath, 80):  # Default quality
                result = {
                    'width': img.width,
                    'height': img.height,
                    'src': str(filepath.relative_to(base_path)),
                    'filesize': filepath.stat().st_size
                }
                log(f"Full-size image saved: {img.width}x{img.height}, {result['filesize']} bytes, {result['src']}")
                trace_out()
                return result
            log(f"Full-size image save FAILED: {img.width}x{img.height} - JPEG write failed")
            trace_out()
            return None
        except Exception as e:
            warn(f"Failed to save full-size image: {str(e)}")
            log(f"Full-size image save FAILED: {img.width}x{img.height} - {str(e)}")
            trace_out()
            return None

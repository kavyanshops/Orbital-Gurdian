"""
Debris Detection Module using Detectron2 Faster R-CNN

This module provides space debris detection in satellite imagery using
a pre-trained Detectron2 model based on Faster R-CNN architecture.
"""

import os
import sys
import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple
import base64
from io import BytesIO
from PIL import Image

# Detectron2 imports - will be conditionally loaded
DETECTRON2_AVAILABLE = False
try:
    import torch
    import detectron2
    from detectron2 import model_zoo
    from detectron2.engine import DefaultPredictor
    from detectron2.config import get_cfg
    from detectron2.utils.visualizer import Visualizer, ColorMode
    from detectron2.data import MetadataCatalog
    DETECTRON2_AVAILABLE = True
except ImportError:
    print("Warning: Detectron2 not installed. Using mock detection mode.")


class DebrisDetector:
    """
    Space debris detector using Detectron2 Faster R-CNN.
    
    If Detectron2 is not available, falls back to mock detection mode
    for demonstration purposes.
    """
    
    def __init__(self, model_weights_path: Optional[str] = None, 
                 confidence_threshold: float = 0.5,
                 use_gpu: bool = True):
        """
        Initialize the debris detector.
        
        Args:
            model_weights_path: Path to trained model weights (model_final.pth).
                              If None, uses COCO pre-trained weights.
            confidence_threshold: Minimum confidence for detection (0-1).
            use_gpu: Whether to use GPU if available.
        """
        self.confidence_threshold = confidence_threshold
        self.model_weights_path = model_weights_path
        self.use_gpu = use_gpu
        self.predictor = None
        self.cfg = None
        self.metadata = None
        
        if DETECTRON2_AVAILABLE:
            self._initialize_detectron2()
        else:
            print("Running in mock mode - Detectron2 not available")
    
    def _initialize_detectron2(self):
        """Initialize Detectron2 model and configuration."""
        self.cfg = get_cfg()
        
        # Use Faster R-CNN with ResNet-50 backbone
        config_file = "COCO-Detection/faster_rcnn_R_50_DC5_3x.yaml"
        self.cfg.merge_from_file(model_zoo.get_config_file(config_file))
        
        # Set model weights
        if self.model_weights_path and os.path.exists(self.model_weights_path):
            self.cfg.MODEL.WEIGHTS = self.model_weights_path
            self.cfg.MODEL.ROI_HEADS.NUM_CLASSES = 1  # Only "Debris" class
            print(f"Loaded custom weights from: {self.model_weights_path}")
        else:
            # Use COCO pre-trained weights for demonstration
            self.cfg.MODEL.WEIGHTS = model_zoo.get_checkpoint_url(config_file)
            print("Using COCO pre-trained weights (demo mode)")
        
        # Configuration
        self.cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = self.confidence_threshold
        
        # Device configuration
        if self.use_gpu and torch.cuda.is_available():
            self.cfg.MODEL.DEVICE = "cuda"
            print("Using GPU for inference")
        else:
            self.cfg.MODEL.DEVICE = "cpu"
            print("Using CPU for inference")
        
        # Create predictor
        self.predictor = DefaultPredictor(self.cfg)
        
        # Set up metadata for visualization
        if self.model_weights_path:
            # Custom trained model - set debris class
            MetadataCatalog.get("debris_inference").set(thing_classes=["Debris"])
            self.metadata = MetadataCatalog.get("debris_inference")
        else:
            # COCO pretrained - use COCO classes
            self.metadata = MetadataCatalog.get(self.cfg.DATASETS.TRAIN[0])
    
    def detect(self, image: np.ndarray) -> Dict:
        """
        Detect debris in an image.
        
        Args:
            image: Input image as numpy array (BGR format from cv2).
            
        Returns:
            Dictionary containing:
                - boxes: List of [x1, y1, x2, y2] bounding boxes
                - scores: List of confidence scores
                - labels: List of class labels
                - num_detections: Total number of detections
        """
        if not DETECTRON2_AVAILABLE:
            return self._mock_detect(image)
        
        # Run inference
        outputs = self.predictor(image)
        instances = outputs["instances"].to("cpu")
        
        # Extract predictions
        boxes = instances.pred_boxes.tensor.numpy().tolist() if len(instances) > 0 else []
        scores = instances.scores.numpy().tolist() if len(instances) > 0 else []
        classes = instances.pred_classes.numpy().tolist() if len(instances) > 0 else []
        
        # Convert class IDs to labels
        if self.model_weights_path:
            labels = ["Debris"] * len(classes)
        else:
            class_names = self.metadata.get("thing_classes", [])
            labels = [class_names[c] if c < len(class_names) else f"class_{c}" 
                     for c in classes]
        
        return {
            "boxes": boxes,
            "scores": scores,
            "labels": labels,
            "num_detections": len(boxes)
        }
    
    def _mock_detect(self, image: np.ndarray) -> Dict:
        """
        Generate mock detections when Detectron2 is not available.
        Useful for testing and demonstration.
        """
        h, w = image.shape[:2]
        
        # Generate 1-5 random mock detections
        num_detections = np.random.randint(1, 6)
        boxes = []
        scores = []
        
        for _ in range(num_detections):
            # Random box dimensions (5-15% of image size)
            box_w = np.random.randint(int(w * 0.05), int(w * 0.15))
            box_h = np.random.randint(int(h * 0.05), int(h * 0.15))
            
            # Random position
            x1 = np.random.randint(0, w - box_w)
            y1 = np.random.randint(0, h - box_h)
            x2 = x1 + box_w
            y2 = y1 + box_h
            
            boxes.append([float(x1), float(y1), float(x2), float(y2)])
            scores.append(float(np.random.uniform(0.5, 0.99)))
        
        return {
            "boxes": boxes,
            "scores": scores,
            "labels": ["Debris"] * num_detections,
            "num_detections": num_detections
        }
    
    def detect_from_path(self, image_path: str) -> Dict:
        """
        Detect debris from an image file path.
        
        Args:
            image_path: Path to the image file.
            
        Returns:
            Detection results dictionary.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not read image: {image_path}")
        
        return self.detect(image)
    
    def detect_from_base64(self, base64_string: str) -> Dict:
        """
        Detect debris from a base64-encoded image.
        
        Args:
            base64_string: Base64-encoded image string.
            
        Returns:
            Detection results dictionary.
        """
        # Remove data URL prefix if present
        if "base64," in base64_string:
            base64_string = base64_string.split("base64,")[1]
        
        # Decode base64
        image_data = base64.b64decode(base64_string)
        image = Image.open(BytesIO(image_data))
        image_array = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        return self.detect(image_array)
    
    def visualize(self, image: np.ndarray, detections: Dict) -> np.ndarray:
        """
        Draw detection results on the image.
        
        Args:
            image: Original image (BGR format).
            detections: Detection results from detect().
            
        Returns:
            Image with visualized detections (RGB format).
        """
        # Convert BGR to RGB for visualization
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        if DETECTRON2_AVAILABLE and self.metadata:
            # Use Detectron2 visualizer
            v = Visualizer(image_rgb, self.metadata, scale=1.0, 
                          instance_mode=ColorMode.IMAGE)
            
            # Create instances-like visualization
            for i, (box, score, label) in enumerate(zip(
                detections["boxes"], 
                detections["scores"], 
                detections["labels"]
            )):
                # Draw box
                x1, y1, x2, y2 = map(int, box)
                color = self._get_confidence_color(score)
                v.draw_box(box, edge_color=color)
                v.draw_text(f"{label}: {score:.2f}", (x1, y1 - 5))
            
            return v.get_output().get_image()
        else:
            # Manual visualization without Detectron2
            return self._manual_visualize(image_rgb, detections)
    
    def _manual_visualize(self, image: np.ndarray, detections: Dict) -> np.ndarray:
        """Manual visualization when Detectron2 is not available."""
        output = image.copy()
        
        for box, score, label in zip(
            detections["boxes"], 
            detections["scores"], 
            detections["labels"]
        ):
            x1, y1, x2, y2 = map(int, box)
            color = self._get_confidence_color(score)
            # Convert color from 0-1 to 0-255
            color_255 = tuple(int(c * 255) for c in color)
            
            # Draw rectangle
            cv2.rectangle(output, (x1, y1), (x2, y2), color_255, 2)
            
            # Draw label background
            label_text = f"{label}: {score:.2f}"
            (text_w, text_h), _ = cv2.getTextSize(
                label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
            )
            cv2.rectangle(output, (x1, y1 - text_h - 10), 
                         (x1 + text_w, y1), color_255, -1)
            
            # Draw label text
            cv2.putText(output, label_text, (x1, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return output
    
    def _get_confidence_color(self, score: float) -> Tuple[float, float, float]:
        """
        Get color based on confidence score.
        High (>0.8): Green, Medium (0.5-0.8): Yellow, Low (<0.5): Red
        """
        if score >= 0.8:
            return (0.2, 0.8, 0.2)  # Green
        elif score >= 0.5:
            return (0.9, 0.7, 0.1)  # Yellow
        else:
            return (0.9, 0.2, 0.2)  # Red
    
    def get_visualization_base64(self, image: np.ndarray, detections: Dict) -> str:
        """
        Get visualization as base64-encoded PNG.
        
        Args:
            image: Original image (BGR format).
            detections: Detection results.
            
        Returns:
            Base64-encoded PNG string.
        """
        vis_image = self.visualize(image, detections)
        
        # Convert to PNG
        is_success, buffer = cv2.imencode(".png", 
                                          cv2.cvtColor(vis_image, cv2.COLOR_RGB2BGR))
        if not is_success:
            raise RuntimeError("Failed to encode visualization image")
        
        return base64.b64encode(buffer).decode("utf-8")


# Singleton instance for API usage
_detector_instance: Optional[DebrisDetector] = None


def get_detector(model_weights_path: Optional[str] = None,
                 confidence_threshold: float = 0.5) -> DebrisDetector:
    """
    Get or create the debris detector singleton.
    
    Args:
        model_weights_path: Path to custom model weights.
        confidence_threshold: Detection confidence threshold.
        
    Returns:
        DebrisDetector instance.
    """
    global _detector_instance
    
    if _detector_instance is None:
        _detector_instance = DebrisDetector(
            model_weights_path=model_weights_path,
            confidence_threshold=confidence_threshold
        )
    
    return _detector_instance

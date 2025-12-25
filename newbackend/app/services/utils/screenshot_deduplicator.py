"""
截图去重工具
使用感知哈希算法检测重复截图
"""

import os
import logging
from typing import List, Dict, Any, Tuple
from PIL import Image
import imagehash

logger = logging.getLogger(__name__)


class DedupResult:
    """去重结果"""
    def __init__(self, keep_results: List[Any], dropped_timepoints: List[Dict[str, str]]):
        self.keep_results = keep_results
        self.dropped_timepoints = dropped_timepoints


class ScreenshotDeduplicator:
    """截图去重器 - 基于感知哈希算法"""

    def __init__(self, hash_threshold: int = 5):
        """
        初始化去重器

        Args:
            hash_threshold: 汉明距离阈值，小于等于该值视为重复图片
        """
        self.hash_threshold = hash_threshold
        logger.info(f"ScreenshotDeduplicator 初始化，哈希阈值: {hash_threshold}")

    def _calculate_dhash(self, image_path: str) -> str:
        """
        计算图片的 dHash（差分哈希）

        Args:
            image_path: 图片路径

        Returns:
            哈希字符串，如果失败返回空字符串
        """
        try:
            if not os.path.exists(image_path):
                logger.warning(f"图片不存在: {image_path}")
                return ""

            with Image.open(image_path) as img:
                # 使用 imagehash 库计算 dHash
                hash_value = imagehash.dhash(img, hash_size=8)
                return str(hash_value)

        except Exception as e:
            logger.error(f"计算图片哈希失败 {image_path}: {e}")
            return ""

    def _calculate_hamming_distance(self, hash1: str, hash2: str) -> int:
        """
        计算两个哈希值的汉明距离

        Args:
            hash1: 第一个哈希值
            hash2: 第二个哈希值

        Returns:
            汉明距离
        """
        if not hash1 or not hash2:
            return 999  # 返回一个很大的值表示不相似

        try:
            # imagehash 返回的字符串可以直接比较
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)
            return h1 - h2  # imagehash 库重载了减法运算符来计算汉明距离
        except Exception as e:
            logger.error(f"计算汉明距离失败: {e}")
            return 999

    async def remove_duplicates(
        self,
        results: List[Any],
        get_image_path_fn=None,
        get_info_score_fn=None,
        get_timepoint_fn=None
    ) -> DedupResult:
        """
        去除重复的截图

        Args:
            results: ScreenshotSelectionResult 列表或包含图片路径的结果列表
            get_image_path_fn: 从结果中获取图片路径的函数，默认使用 result.selected[0]
            get_info_score_fn: 从结果中获取信息评分的函数，默认返回 0
            get_timepoint_fn: 从结果中获取时间点的函数，默认使用 result.timepoint

        Returns:
            DedupResult: 包含保留的结果和被丢弃的时间点信息
        """
        if not results:
            return DedupResult(keep_results=[], dropped_timepoints=[])

        logger.info(f"开始去重处理，共 {len(results)} 个截图")

        # 默认的访问函数
        if get_image_path_fn is None:
            get_image_path_fn = lambda r: r.selected[0] if r.selected else ""
        if get_info_score_fn is None:
            get_info_score_fn = lambda r: getattr(r, 'info_score', 0.0)
        if get_timepoint_fn is None:
            get_timepoint_fn = lambda r: r.timepoint

        # 第一步：为每个结果计算哈希值
        result_with_hash = []
        for result in results:
            try:
                image_path = get_image_path_fn(result)
                if not image_path:
                    logger.warning(f"结果中没有图片路径，跳过: {result}")
                    continue

                hash_value = self._calculate_dhash(image_path)
                info_score = get_info_score_fn(result)
                timepoint = get_timepoint_fn(result)

                result_with_hash.append({
                    'result': result,
                    'hash': hash_value,
                    'info_score': info_score,
                    'timepoint': timepoint,
                    'image_path': image_path
                })

            except Exception as e:
                logger.error(f"处理结果时出错: {e}")
                continue

        if not result_with_hash:
            logger.warning("没有有效的结果可以去重")
            return DedupResult(keep_results=results, dropped_timepoints=[])

        # 第二步：检测重复并决定保留哪些
        keep_results = []
        dropped_timepoints = []
        processed_hashes = []  # 已经处理过的哈希值

        for item in result_with_hash:
            is_duplicate = False
            duplicate_with = None

            # 与已保留的所有图片比较
            for kept_item in processed_hashes:
                distance = self._calculate_hamming_distance(item['hash'], kept_item['hash'])

                if distance <= self.hash_threshold:
                    # 发现重复
                    is_duplicate = True

                    # 比较信息评分，保留评分更高的
                    if item['info_score'] > kept_item['info_score']:
                        # 当前图片更好，替换之前保留的
                        logger.info(
                            f"发现重复截图，保留信息评分更高的: "
                            f"{item['timepoint']} (score: {item['info_score']:.3f}) > "
                            f"{kept_item['timepoint']} (score: {kept_item['info_score']:.3f}), "
                            f"汉明距离: {distance}"
                        )

                        # 标记之前保留的为待丢弃
                        keep_results.remove(kept_item['result'])
                        dropped_timepoints.append({
                            'timepoint': kept_item['timepoint'],
                            'drop_reason': f'被信息评分更高的截图替换 (distance={distance})',
                            'kept_with': item['timepoint']
                        })

                        # 更新已处理的哈希
                        processed_hashes.remove(kept_item)
                        processed_hashes.append(item)
                        keep_results.append(item['result'])
                        duplicate_with = None  # 重置，因为我们保留了当前的
                        is_duplicate = False  # 重置，因为我们保留了当前的
                    else:
                        # 之前的图片更好，丢弃当前的
                        duplicate_with = kept_item['timepoint']
                        logger.info(
                            f"发现重复截图，丢弃信息评分较低的: "
                            f"{item['timepoint']} (score: {item['info_score']:.3f}) < "
                            f"{kept_item['timepoint']} (score: {kept_item['info_score']:.3f}), "
                            f"汉明距离: {distance}"
                        )
                    break

            if is_duplicate and duplicate_with:
                # 记录被丢弃的时间点
                dropped_timepoints.append({
                    'timepoint': item['timepoint'],
                    'drop_reason': f'与时间点 {duplicate_with} 的截图重复',
                    'kept_with': duplicate_with
                })
            elif not is_duplicate:
                # 不是重复的，保留
                keep_results.append(item['result'])
                processed_hashes.append(item)

        logger.info(
            f"去重完成: 保留 {len(keep_results)} 个截图, "
            f"丢弃 {len(dropped_timepoints)} 个重复截图 "
            f"(哈希阈值 <= {self.hash_threshold})"
        )

        if dropped_timepoints:
            logger.debug(f"被丢弃的时间点: {[d['timepoint'] for d in dropped_timepoints]}")

        return DedupResult(
            keep_results=keep_results,
            dropped_timepoints=dropped_timepoints
        )

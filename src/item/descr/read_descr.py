import logging

import numpy as np

from src.config.ui import ResManager
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.descr.find_affixes import find_affixes
from src.item.descr.find_aspect import find_aspect
from src.item.descr.item_type import read_item_type
from src.item.descr.texture import find_affix_bullets, find_aspect_bullet, find_codex_upgrade_icon, find_empty_sockets, find_seperator_short
from src.item.models import Item
from src.utils.window import screenshot

LOGGER = logging.getLogger(__name__)


def read_descr(rarity: ItemRarity, img_item_descr: np.ndarray, show_warnings: bool = True) -> Item | None:
    base_item = Item(rarity=rarity)

    # Find textures for seperator short on top
    # =========================
    sep_short_match = find_seperator_short(img_item_descr)
    if sep_short_match is None:
        if show_warnings:
            LOGGER.warning("Could not detect item_seperator_short.")
            screenshot("failed_seperator_short", img=img_item_descr)
        return None

    # Find item type and item power / tier list
    # =========================
    item, item_type_str = read_item_type(base_item, img_item_descr, sep_short_match, do_pre_proc=False)
    # In case it was not successful, try with doing image pre-processing
    if item is None:
        item, item_type_str = read_item_type(base_item, img_item_descr, sep_short_match)
    if item is None:
        if show_warnings:
            LOGGER.warning(f"Could not detect ItemPower and ItemType: {item_type_str}")
            screenshot("failed_itempower_itemtype", img=img_item_descr)
        return None

    if item.item_type in [ItemType.Material, ItemType.TemperManual, ItemType.Elixir] or (
        item.rarity in [ItemRarity.Magic, ItemRarity.Common] and item.item_type != ItemType.Sigil
    ):
        return item

    # Find textures for bullets and sockets
    # =========================
    affix_bullets = find_affix_bullets(img_item_descr, sep_short_match)
    aspect_bullet = find_aspect_bullet(img_item_descr, sep_short_match) if rarity in [ItemRarity.Legendary, ItemRarity.Unique] else None
    item.codex_upgrade = find_codex_upgrade_icon(img_item_descr, aspect_bullet)
    empty_sockets = find_empty_sockets(img_item_descr, sep_short_match)

    # Split affix bullets into inherent and others
    # =========================
    if item.item_type in [ItemType.ChestArmor, ItemType.Helm, ItemType.Gloves, ItemType.Legs]:
        inhernet_affixe_bullets = []
    elif item.item_type in [ItemType.Ring]:
        inhernet_affixe_bullets = affix_bullets[:2]
        affix_bullets = affix_bullets[2:]
    elif item.item_type in [ItemType.Sigil]:
        inhernet_affixe_bullets = affix_bullets[:3]
        affix_bullets = affix_bullets[3:]
    elif item.item_type in [ItemType.Shield]:
        inhernet_affixe_bullets = affix_bullets[:4]
        affix_bullets = affix_bullets[4:]
    else:
        # default for: Amulets, Boots, All Weapons
        inhernet_affixe_bullets = affix_bullets[:1]
        affix_bullets = affix_bullets[1:]

    # Find inherent affixes
    # =========================
    is_sigil = item.item_type == ItemType.Sigil
    line_height = ResManager().offsets.item_descr_line_height
    if len(inhernet_affixe_bullets) > 0 and len(affix_bullets) > 0:
        bottom_limit = affix_bullets[0].center[1] - int(line_height // 2)
        item.inherent, debug_str = find_affixes(
            img_item_descr=img_item_descr,
            affix_bullets=inhernet_affixe_bullets,
            bottom_limit=bottom_limit,
            is_sigil=is_sigil,
            is_inherent=True,
        )
        if item.inherent is None:
            item.inherent, debug_str = find_affixes(
                img_item_descr=img_item_descr,
                affix_bullets=inhernet_affixe_bullets,
                bottom_limit=bottom_limit,
                is_sigil=is_sigil,
                is_inherent=True,
                do_pre_proc_flag=False,
            )
        if item.inherent is None:
            if show_warnings:
                LOGGER.warning(f"Could not find inherent: {debug_str}")
                screenshot("failed_inherent", img=img_item_descr)
            return None

    # Find normal affixes
    # =========================
    if aspect_bullet is not None:
        bottom_limit = aspect_bullet.center[1]
    elif len(empty_sockets) > 0:
        bottom_limit = empty_sockets[0].center[1]
    else:
        bottom_limit = img_item_descr.shape[0]
    item.affixes, debug_str = find_affixes(
        img_item_descr=img_item_descr, affix_bullets=affix_bullets, bottom_limit=bottom_limit, is_sigil=is_sigil
    )
    if item.affixes is None:
        item.affixes, debug_str = find_affixes(
            img_item_descr=img_item_descr, affix_bullets=affix_bullets, bottom_limit=bottom_limit, is_sigil=is_sigil, do_pre_proc_flag=False
        )
    if item.affixes is None:
        if show_warnings:
            LOGGER.warning(f"Could not find affix: {debug_str}")
            screenshot("failed_affixes", img=img_item_descr)
        return None

    # Find aspects of uniques
    # =========================
    if rarity == ItemRarity.Unique:
        item.aspect, debug_str = find_aspect(img_item_descr, aspect_bullet)
        if item.aspect is None:
            item.aspect, debug_str = find_aspect(img_item_descr, aspect_bullet, False)
        if item.aspect is None:
            if show_warnings:
                LOGGER.warning(f"Could not find unique: {debug_str}")
                screenshot("failed_aspect_or_unique", img=img_item_descr)
            return None

    return item

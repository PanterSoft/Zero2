from modules.logger import get_logger

logger = get_logger(__name__)

class MenuSystem:
    """
    Menu navigation system for the display.
    Handles menu state and navigation.
    """

    MENU_MAIN = "main"
    MENU_NETWORK = "network"
    MENU_SYSTEM = "system"
    MENU_POWER = "power"

    def __init__(self):
        self.current_menu = self.MENU_MAIN
        self.menu_stack = [self.MENU_MAIN]
        self.selected_index = 0

        # Menu items for each menu
        self.menu_items = {
            self.MENU_MAIN: [
                {"name": "Dashboard", "action": self.MENU_MAIN},
                {"name": "Network Info", "action": self.MENU_NETWORK},
                {"name": "System Info", "action": self.MENU_SYSTEM},
                {"name": "Power Info", "action": self.MENU_POWER},
            ],
            self.MENU_NETWORK: [
                {"name": "Back", "action": "back"},
            ],
            self.MENU_SYSTEM: [
                {"name": "Back", "action": "back"},
            ],
            self.MENU_POWER: [
                {"name": "Back", "action": "back"},
            ],
        }

    def navigate_up(self):
        """Navigate up in menu."""
        try:
            if self.current_menu == self.MENU_MAIN:
                # In main menu, cycle through items
                self.selected_index = (self.selected_index - 1) % len(self.menu_items[self.MENU_MAIN])
                logger.debug(f"Menu UP: selected_index={self.selected_index}")
            else:
                # In submenu, go back
                self.go_back()
        except Exception as e:
            logger.error(f"Error in navigate_up: {e}", exc_info=True)

    def navigate_down(self):
        """Navigate down in menu."""
        try:
            if self.current_menu == self.MENU_MAIN:
                # In main menu, cycle through items
                self.selected_index = (self.selected_index + 1) % len(self.menu_items[self.MENU_MAIN])
                logger.debug(f"Menu DOWN: selected_index={self.selected_index}")
            else:
                # In submenu, go back
                self.go_back()
        except Exception as e:
            logger.error(f"Error in navigate_down: {e}", exc_info=True)

    def navigate_left(self):
        """Navigate left (go back)."""
        try:
            self.go_back()
        except Exception as e:
            logger.error(f"Error in navigate_left: {e}", exc_info=True)

    def navigate_right(self):
        """Navigate right (select/enter)."""
        try:
            if self.current_menu == self.MENU_MAIN:
                item = self.menu_items[self.MENU_MAIN][self.selected_index]
                if item["action"] != self.MENU_MAIN:
                    self.enter_menu(item["action"])
            else:
                # In submenu, go back
                self.go_back()
        except Exception as e:
            logger.error(f"Error in navigate_right: {e}", exc_info=True)

    def select(self):
        """Select current menu item."""
        try:
            if self.current_menu == self.MENU_MAIN:
                item = self.menu_items[self.MENU_MAIN][self.selected_index]
                if item["action"] == self.MENU_MAIN:
                    # Already on dashboard
                    logger.debug("Already on dashboard")
                else:
                    self.enter_menu(item["action"])
            else:
                self.go_back()
        except Exception as e:
            logger.error(f"Error in select: {e}", exc_info=True)

    def enter_menu(self, menu_name):
        """Enter a submenu."""
        if menu_name in self.menu_items:
            self.menu_stack.append(self.current_menu)
            self.current_menu = menu_name
            self.selected_index = 0
            logger.debug(f"Entered menu: {menu_name}")

    def go_back(self):
        """Go back to previous menu."""
        if len(self.menu_stack) > 1:
            self.current_menu = self.menu_stack.pop()
            self.selected_index = 0
            logger.debug(f"Returned to menu: {self.current_menu}")
        else:
            # Return to main menu (dashboard)
            self.current_menu = self.MENU_MAIN
            self.menu_stack = [self.MENU_MAIN]
            self.selected_index = 0

    def get_current_menu(self):
        """Get current menu name."""
        return self.current_menu

    def get_menu_items(self):
        """Get items for current menu."""
        return self.menu_items.get(self.current_menu, [])

    def get_selected_index(self):
        """Get currently selected index."""
        return self.selected_index

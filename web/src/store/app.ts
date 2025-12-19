import { User } from '@/types';
import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useAppStore = defineStore('app', () => {
    const theme = ref<"dark" | "light">("light");
    const openSidebars = ref<("left" | "right")[]>(["left"]);
    const currentUser = ref<User>();
    const currentError = ref<string>();

    function setDefaultTheme() {
        const darkThemeMatch = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
        theme.value = darkThemeMatch ? "dark" : "light";

        return theme.value;
    }

    return {
        theme,
        openSidebars,
        currentUser,
        currentError,
        setDefaultTheme,
    }
});

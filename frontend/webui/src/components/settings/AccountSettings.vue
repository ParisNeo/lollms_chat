<script setup>
import { ref, onMounted, computed } from 'vue';
import { useAuthStore } from '../../stores/auth';
import { useUiStore } from '../../stores/ui';
import apiClient from '../../services/api'; // Import apiClient for direct use
import UserAvatar from '../ui/UserAvatar.vue'; // --- NEW: Import the avatar component

const authStore = useAuthStore();
const uiStore = useUiStore();

// --- Computed property for reactive user data ---
const user = computed(() => authStore.user);

// --- Profile Form State ---
const profileForm = ref({
    first_name: '',
    family_name: '',
    email: '',
    birth_date: ''
});
const isProfileLoading = ref(false);

// --- Password Form State ---
const passwordForm = ref({
    current_password: '',
    new_password: ''
});
const confirmNewPassword = ref('');
const isPasswordLoading = ref(false);
const showCurrentPassword = ref(false);
const showNewPassword = ref(false);

// --- NEW: Icon upload state ---
const isUploadingIcon = ref(false);
const fileInput = ref(null);


// Populate form when component mounts or user data changes
onMounted(() => {
    if (user.value) {
        profileForm.value.first_name = user.value.first_name || '';
        profileForm.value.family_name = user.value.family_name || '';
        profileForm.value.email = user.value.email || '';
        profileForm.value.birth_date = user.value.birth_date || '';
    }
});

// --- Actions ---

async function handleSaveProfile() {
    isProfileLoading.value = true;
    try {
        await authStore.updateUserProfile(profileForm.value);
    } catch (error) {
        // Error is handled by API interceptor
    } finally {
        isProfileLoading.value = false;
    }
}

async function handleChangePassword() {
    if (passwordForm.value.new_password !== confirmNewPassword.value) {
        uiStore.addNotification("New passwords do not match.", 'error');
        return;
    }
    if (passwordForm.value.new_password.length < 8) {
        uiStore.addNotification("New password must be at least 8 characters long.", 'error');
        return;
    }

    isPasswordLoading.value = true;
    try {
        await authStore.changePassword(passwordForm.value);
        passwordForm.value.current_password = '';
        passwordForm.value.new_password = '';
        confirmNewPassword.value = '';
    } catch (error) {
        // Error handled by interceptor
    } finally {
        isPasswordLoading.value = false;
    }
}

// --- NEW: Icon upload logic ---
const triggerFileInput = () => {
  fileInput.value?.click();
};

const onIconFileChange = async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  isUploadingIcon.value = true;
  uiStore.addNotification('Uploading icon...', 'info');

  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await apiClient.put('/api/auth/me/icon', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    
    // The backend returns the new Base64 URI. Update the user in the auth store.
    if (authStore.user) {
      authStore.user.icon = response.data.icon_url;
    }
    
    uiStore.addNotification('Icon updated successfully!', 'success');
  } catch (error) {
    // The global interceptor will show the detailed error message
    uiStore.addNotification('Icon upload failed.', 'error');
  } finally {
    isUploadingIcon.value = false;
    if (fileInput.value) {
      fileInput.value.value = ''; // Reset input
    }
  }
};
</script>

<template>
    <div v-if="user" class="space-y-10">
        <!-- User Profile Section -->
        <div class="bg-white dark:bg-gray-800 shadow-md rounded-lg">
            <div class="p-4 sm:p-6">
                <h2 class="text-xl font-bold leading-6 text-gray-900 dark:text-white">Profile</h2>
                <p class="mt-1 max-w-2xl text-sm text-gray-500 dark:text-gray-400">Manage your public profile and personal information.</p>
            </div>
            <div class="border-t border-gray-200 dark:border-gray-700 p-4 sm:p-6">
                <form @submit.prevent="handleSaveProfile" class="flex flex-col md:flex-row gap-8">
                    <!-- Avatar Section -->
                    <div class="flex-shrink-0 flex flex-col items-center space-y-2 w-full md:w-40">
                        <UserAvatar :icon="user.icon" :username="user.username" size-class="h-28 w-28" />
                        <input
                            type="file"
                            ref="fileInput"
                            @change="onIconFileChange"
                            accept="image/png, image/jpeg, image/webp"
                            class="hidden"
                        />
                        <button
                            type="button"
                            @click="triggerFileInput"
                            :disabled="isUploadingIcon"
                            class="btn btn-secondary w-full"
                        >
                            {{ isUploadingIcon ? 'Uploading...' : 'Change Icon' }}
                        </button>
                        <p class="text-xs text-center text-gray-500 dark:text-gray-400">Max 5MB (JPG, PNG, WEBP)</p>
                    </div>

                    <!-- Profile Info Form -->
                    <div class="flex-grow space-y-6">
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
                            <div>
                                <label for="firstName" class="block text-sm font-medium text-gray-700 dark:text-gray-300">First Name</label>
                                <input type="text" id="firstName" v-model="profileForm.first_name" class="input-field mt-1" placeholder="Jane">
                            </div>
                            <div>
                                <label for="familyName" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Family Name</label>
                                <input type="text" id="familyName" v-model="profileForm.family_name" class="input-field mt-1" placeholder="Doe">
                            </div>
                        </div>
                        <div>
                            <label for="email" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Email Address</label>
                            <input type="email" id="email" v-model="profileForm.email" class="input-field mt-1" placeholder="you@example.com">
                        </div>
                        <div>
                            <label for="birthDate" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Birth Date</label>
                            <input type="date" id="birthDate" v-model="profileForm.birth_date" class="input-field mt-1">
                        </div>
                        <div class="flex justify-end">
                            <button type="submit" class="btn btn-primary" :disabled="isProfileLoading">
                                {{ isProfileLoading ? 'Saving...' : 'Save Profile' }}
                            </button>
                        </div>
                    </div>
                </form>
            </div>
        </div>

        <!-- Change Password Section -->
        <div class="bg-white dark:bg-gray-800 shadow-md rounded-lg">
             <div class="px-4 py-5 sm:p-6">
                <h2 class="text-xl font-bold leading-6 text-gray-900 dark:text-white">Change Password</h2>
                <p class="mt-1 max-w-2xl text-sm text-gray-500 dark:text-gray-400">Ensure your account is using a long, random password to stay secure.</p>
            </div>
             <div class="border-t border-gray-200 dark:border-gray-700">
                <form @submit.prevent="handleChangePassword" class="p-4 sm:p-6 space-y-6">
                    <div>
                        <label for="currentPassword" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Current Password</label>
                        <div class="mt-1 relative">
                            <input :type="showCurrentPassword ? 'text' : 'password'" id="currentPassword" v-model="passwordForm.current_password" required class="input-field pr-10" autocomplete="current-password">
                            <button type="button" @click="showCurrentPassword = !showCurrentPassword" class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
                                <svg v-if="!showCurrentPassword" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" /><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
                                <svg v-else xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.243 4.243L6.228 6.228" /></svg>
                            </button>
                        </div>
                    </div>
                    <div>
                        <label for="newPassword" class="block text-sm font-medium text-gray-700 dark:text-gray-300">New Password</label>
                         <div class="mt-1 relative">
                            <input :type="showNewPassword ? 'text' : 'password'" id="newPassword" v-model="passwordForm.new_password" required minlength="8" class="input-field pr-10" autocomplete="new-password">
                            <button type="button" @click="showNewPassword = !showNewPassword" class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
                                <svg v-if="!showNewPassword" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" /><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
                                <svg v-else xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.243 4.243L6.228 6.228" /></svg>
                            </button>
                        </div>
                    </div>
                    <div>
                        <label for="confirmPassword" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Confirm New Password</label>
                        <div class="mt-1 relative">
                            <input :type="showNewPassword ? 'text' : 'password'" id="confirmPassword" v-model="confirmNewPassword" required class="input-field pr-10" autocomplete="new-password">
                        </div>
                    </div>
                    <div class="flex justify-end">
                        <button type="submit" class="btn btn-primary" :disabled="isPasswordLoading">
                            {{ isPasswordLoading ? 'Changing...' : 'Change Password' }}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</template>
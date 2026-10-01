document.addEventListener('DOMContentLoaded', () => {
  const searchForm = document.getElementById('searchForm');
  const adminForm = document.getElementById('adminUploadForm');
  const imageInput = document.getElementById('imageUpload');
  const imagePreview = document.getElementById('imagePreview');
  const previewPlaceholder = document.getElementById('previewPlaceholder');
  const toastContainer = document.getElementById('toastContainer');
  const lightbox = document.getElementById('lightbox');
  const lightboxImage = lightbox?.querySelector('img');
  const closeLightboxButton = document.querySelector('.lightbox-close');
  const modal = document.getElementById('confirmModal');
  const cancelDelete = document.getElementById('cancelDelete');
  const confirmDelete = document.getElementById('confirmDelete');

  function showToast(message, type = 'success') {
    if (!toastContainer || !message) {
      return;
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.remove();
    }, 3200);
  }

  if (window.appMessages && window.appMessages.success) {
    showToast(window.appMessages.success, 'success');
  }

  if (window.appMessages && window.appMessages.error) {
    showToast(window.appMessages.error, 'error');
  }

  if (imageInput) {
    imageInput.addEventListener('change', (event) => {
      const file = event.target.files[0];
      if (!file) {
        return;
      }

      const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
      const validExtensions = ['jpg', 'jpeg', 'png', 'webp'];
      const extension = file.name.split('.').pop().toLowerCase();

      if (!validExtensions.includes(extension) || !validTypes.includes(file.type)) {
        showToast('Unsupported image format. Use JPG, JPEG, PNG, or WEBP.', 'error');
        imageInput.value = '';
        imagePreview.classList.add('hidden');
        previewPlaceholder.classList.remove('hidden');
        return;
      }

      const reader = new FileReader();
      reader.onload = (loadEvent) => {
        imagePreview.src = loadEvent.target.result;
        imagePreview.classList.remove('hidden');
        previewPlaceholder.classList.add('hidden');
      };
      reader.readAsDataURL(file);
    });
  }

  if (searchForm) {
    searchForm.addEventListener('submit', (event) => {
      const yearInput = searchForm.querySelector('#year');
      const monthInput = searchForm.querySelector('#month');
      const naturalInput = searchForm.querySelector('#search_query');
      const searchButton = searchForm.querySelector('#searchButton');
      const spinner = searchButton?.querySelector('.spinner');
      const buttonText = searchButton?.querySelector('.button-text');

      if (yearInput && !yearInput.value && monthInput && !monthInput.value && naturalInput && naturalInput.value.trim()) {
        const query = naturalInput.value.trim();
        const yearMatch = query.match(/(19\d{2}|20\d{2}|21\d{2})/);
        const monthMatch = query.match(/january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec/i);
        const monthMap = {
          jan: 'January', january: 'January',
          feb: 'February', february: 'February',
          mar: 'March', march: 'March',
          apr: 'April', april: 'April',
          may: 'May',
          jun: 'June', june: 'June',
          jul: 'July', july: 'July',
          aug: 'August', august: 'August',
          sep: 'September', sept: 'September', september: 'September',
          oct: 'October', october: 'October',
          nov: 'November', november: 'November',
          dec: 'December', december: 'December'
        };

        if (yearMatch) {
          yearInput.value = yearMatch[1];
        }

        if (monthMatch) {
          const key = monthMatch[0].toLowerCase();
          monthInput.value = monthMap[key] || monthMatch[0];
        }
      }

      if (!yearInput?.value || !monthInput?.value) {
        if (!yearInput?.value || !monthInput?.value) {
          const hasNaturalQuery = naturalInput && naturalInput.value.trim();
          if (!hasNaturalQuery) {
            event.preventDefault();
            showToast('Please provide both a year and month.', 'error');
            return;
          }
        }
      }

      if (spinner && buttonText) {
        spinner.classList.remove('hidden');
        buttonText.textContent = 'Searching...';
        searchButton.disabled = true;
      }
    });
  }

  if (adminForm) {
    adminForm.addEventListener('submit', (event) => {
      const yearInput = document.getElementById('adminYear');
      const monthInput = document.getElementById('adminMonth');
      const uploadFile = document.getElementById('imageUpload');
      const button = document.getElementById('uploadButton');
      const spinner = button?.querySelector('.spinner');
      const buttonText = button?.querySelector('.button-text');

      const validYear = yearInput && yearInput.value.trim();
      const validMonth = monthInput && monthInput.value.trim();
      const validFile = uploadFile && uploadFile.files && uploadFile.files.length > 0;

      if (!validYear || !validMonth || !validFile) {
        event.preventDefault();
        showToast('Please complete the upload form with a year, month, and image.', 'error');
        return;
      }

      if (spinner && buttonText) {
        spinner.classList.remove('hidden');
        buttonText.textContent = 'Uploading...';
        button.disabled = true;
      }
    });
  }

  const makeDeleteRequest = async (imageId) => {
    const response = await fetch(`/delete/${imageId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });

    const data = await response.json();
    if (!response.ok || !data.success) {
      throw new Error(data.message || 'Unable to delete this image.');
    }

    return data;
  };

  let pendingDeleteId = null;

  document.querySelectorAll('.delete-btn').forEach((button) => {
    button.addEventListener('click', () => {
      pendingDeleteId = Number(button.dataset.deleteId);
      if (modal) {
        modal.classList.remove('hidden');
      }
    });
  });

  if (cancelDelete) {
    cancelDelete.addEventListener('click', () => {
      if (modal) {
        modal.classList.add('hidden');
      }
      pendingDeleteId = null;
    });
  }

  if (confirmDelete) {
    confirmDelete.addEventListener('click', async () => {
      if (!pendingDeleteId) {
        return;
      }

      try {
        await makeDeleteRequest(pendingDeleteId);
        const card = document.querySelector(`[data-image-id="${pendingDeleteId}"]`);
        if (card) {
          card.remove();
        }

        showToast('Image deleted successfully.', 'success');
      } catch (error) {
        showToast(error.message, 'error');
      } finally {
        if (modal) {
          modal.classList.add('hidden');
        }
        pendingDeleteId = null;
      }
    });
  }

  document.querySelectorAll('.lightbox-trigger').forEach((trigger) => {
    trigger.addEventListener('click', () => {
      if (!lightbox || !lightboxImage) {
        return;
      }

      lightboxImage.src = trigger.dataset.image;
      lightboxImage.alt = trigger.dataset.alt || 'Expanded image';
      lightbox.classList.remove('hidden');
    });
  });

  if (closeLightboxButton) {
    closeLightboxButton.addEventListener('click', () => {
      if (lightbox) {
        lightbox.classList.add('hidden');
      }
    });
  }

  if (lightbox) {
    lightbox.addEventListener('click', (event) => {
      if (event.target === lightbox) {
        lightbox.classList.add('hidden');
      }
    });
  }

  window.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      if (lightbox) {
        lightbox.classList.add('hidden');
      }
      if (modal) {
        modal.classList.add('hidden');
      }
    }
  });
});

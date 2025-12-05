package com.example.ailoanadvisor

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import com.example.ailoanadvisor.databinding.ActivityProfileBinding
import com.google.firebase.auth.FirebaseAuth

class ProfileActivity : AppCompatActivity() {

    private lateinit var binding: ActivityProfileBinding

    // ✅ Image Picker
    private val imagePicker =
        registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
            if (uri != null) {
                saveImageUri(uri)
                binding.imgProfile.setImageURI(uri)
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityProfileBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val user = FirebaseAuth.getInstance().currentUser
        binding.tvEmail.text = user?.email ?: "No Email"

        // ✅ Load saved user name
        val prefs = getSharedPreferences("user_prefs", MODE_PRIVATE)
        val userName = prefs.getString("user_name", "User")
        binding.tvName.text = userName

        // ✅ Load Saved Image on Open
        loadSavedImage()

        // ✅ Change Photo Button
        binding.btnChangePhoto.setOnClickListener {
            imagePicker.launch("image/*")
        }

        // ✅ Open Settings
        binding.btnSettings.setOnClickListener {
            startActivity(Intent(this, SettingsActivity::class.java))
        }

        // ✅ Logout
        binding.btnLogout.setOnClickListener {
            FirebaseAuth.getInstance().signOut()
            val intent = Intent(this, LoginActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            }
            startActivity(intent)
            finish()
        }
    }

    // ✅ Save Image URI Permanently
    private fun saveImageUri(uri: Uri) {
        val prefs = getSharedPreferences("profile_prefs", MODE_PRIVATE)
        prefs.edit().putString("profile_image", uri.toString()).apply()
    }

    // ✅ Load Image on App Restart
    private fun loadSavedImage() {
        val prefs = getSharedPreferences("profile_prefs", MODE_PRIVATE)
        val savedUri = prefs.getString("profile_image", null)
        if (savedUri != null) {
            binding.imgProfile.setImageURI(Uri.parse(savedUri))
        }
    }
}

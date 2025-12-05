package com.example.ailoanadvisor

import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.example.ailoanadvisor.databinding.ActivityEligibilityBinding

class EligibilityActivity : AppCompatActivity() {

    // Use ViewBinding for safer and cleaner view access
    private lateinit var binding: ActivityEligibilityBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityEligibilityBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // The Spinner is populated from the XML layout (`android:entries`),
        // so we don't need to set an adapter here.

        binding.btnCheck.setOnClickListener {
            // Get text from input fields
            val ageStr = binding.etAge.text.toString()
            val incomeStr = binding.etIncome.text.toString()
            val emiStr = binding.etEmi.text.toString()
            val jobType = binding.spinnerJob.selectedItem.toString()

            // Validate that inputs are not empty
            if (ageStr.isEmpty() || incomeStr.isEmpty() || emiStr.isEmpty()) {
                Toast.makeText(this, getString(R.string.eligibility_fill_all_fields), Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            // Data is collected, but no local eligibility check is performed.
            // This data would typically be sent to a server.
            // For now, just display a confirmation message.
            binding.tvResult.text = getString(R.string.eligibility_form_submitted)
            Toast.makeText(this, getString(R.string.eligibility_submission_successful), Toast.LENGTH_LONG).show()
        }
    }
}

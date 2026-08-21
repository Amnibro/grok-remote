plugins{id("com.android.application");kotlin("android")}
android{
 namespace="com.amniscient.grokremote.wear"
 compileSdk=34
 defaultConfig{applicationId="com.amniscient.grokremote.wear";minSdk=30;targetSdk=34;versionCode=1;versionName="1.0"}
 compileOptions{sourceCompatibility=JavaVersion.VERSION_17;targetCompatibility=JavaVersion.VERSION_17}
 kotlinOptions{jvmTarget="17"}
}
